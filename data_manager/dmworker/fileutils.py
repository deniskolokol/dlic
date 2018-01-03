import os
import re
import io
import gzip
import tarfile
import hashlib
import tempfile
import subprocess as sp
from bz2 import BZ2File
from unipath import Path, FSPath

# this is why we are not using original zipfile
# http://bugs.python.org/issue20048
import sys
ver = sys.version_info
if ver.major == 2 and ver.minor == 7 and ver.micro < 7:
    from . import fixed_zipfile as zipfile
else:
    import zipfile

def open_file(filename):
    with open(filename, 'rU') as f:
        for line in f:
            yield line.strip()


def open_gz(filename):
    with gzip.open(filename) as f:
        for line in io.TextIOWrapper(io.BufferedReader(f)):
            yield line.strip()


def open_bz(filename):
    with BZ2File(filename, 'rU') as f:
        for line in f:
            yield line.strip()


class InvalidArchive(Exception):
    pass


class ProcessCall(object):
    def __init__(self, proc, *args):
        self.args = [str(a) for a in args]
        self.process = [proc] + self.args

    def call(self):
        proc = sp.Popen(self.process, stdout=sp.PIPE, stderr=sp.PIPE)
        content, errors = proc.communicate()
        return content, errors


class Archive(object):
    def __init__(self, archive):
        self.is_zipfile = False
        self.filename = archive
        if archive.lower().endswith('.zip'):
            if not zipfile.is_zipfile(archive):
                raise InvalidArchive('Not a zip archive')
            self.is_zipfile = True
            self.loaded = False
        elif archive.lower().endswith(('.tar.bz', '.tar.bz2', '.tar.gz')):
            if not tarfile.is_tarfile(archive):
                raise InvalidArchive('Not a tar archive')
            self._archive = tarfile.open(archive)
            self.loaded = True
        else:
            raise InvalidArchive()

    def load(self):
        self._archive = zipfile.ZipFile(self.filename)
        self.loaded = True

    def __iter__(self):
        def unzip():
            with TempFile() as tf:
                with open(tf, 'w') as tf_:
                    sp.call(['unzip', '-l', self.filename], stdout=tf_)
                with open(tf) as f:
                    for line in f:
                        if line.startswith('-'):
                            break
                    for line in f:
                        if line.startswith('-'):
                            break
                        yield line.strip().split(None, 3)[-1]

        def untar():
            with TempFile() as tf:
                with open(tf, 'w') as tf_:
                    sp.call(['tar', '-tf', self.filename], stdout=tf_)
                with open(tf) as f:
                    for line in f:
                        yield line.strip()

        if self.is_zipfile:
            return unzip()
        else:
            return untar()

    def get_members(self):
        return [x for x in self]

    def open_raw_member(self, member):
        if not self.loaded:
            self.load()
        if self.is_zipfile:
            return self._archive.open(member)
        else:
            return self._archive.extractfile(member)

    def open_member(self, member):
        if not self.loaded:
            self.load()
        if self.is_zipfile:
            for line in self._archive.open(member, 'rU'):
                yield line
        else:
            #TODO: change to bf reader?, check size
            with TempFile() as tf:
                with open(tf, 'w') as f:
                    m = self._archive.extractfile(member)
                    while True:
                        data = m.read(1024*1024)
                        if data == '':
                            break
                        f.write(data)
                for line in open_file(tf):
                    yield line

    def get_member_size(self, member):
        if not self.loaded:
            self.load()
        if self.is_zipfile:
            return self._archive.getinfo(member).file_size
        else:
            return self._archive.getmember(member).size

    @staticmethod
    def get_img_class(member):
        if re.search(r'^\.[^\/\.]', member):
            return None
        if re.search(r'\/\.[^\/\.]', member):
            return None
        member = Path(member.lstrip('./'))
        if member.parent:
            return member.parent
        return None

    def close(self):
        if not self.loaded:
            return
        self._archive.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def md5(file_path, blocksize=65536):
    with open(file_path) as f:
        hasher = hashlib.md5()
        buf = f.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(blocksize)
        return hasher.hexdigest()


class cwd(object):
    def __init__(self, cwd):
        self.prev_cwd = FSPath.cwd()
        self.cwd = Path(cwd)
        if not self.cwd.exists():
            self.cwd.mkdir(parents=True)

    def __enter__(self):
        self.cwd.chdir()
        return self.cwd

    def __exit__(self, type_, value, traceback):
        self.prev_cwd.chdir()


def zip_write(zip_file, fp, name=None):
    fp = Path(fp)
    with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        with cwd(fp.parent):
            z.write(fp.name, arcname=name)
    return zip_file


class TempFile(object):
    def __init__(self, data='', **kwargs):
        self._f = tempfile.NamedTemporaryFile(delete=False, **kwargs)
        self._f.write(data)
        self._f.close()

    def __enter__(self):
        return self._f.name

    def __exit__(self, *args):
        os.unlink(self._f.name)


class tempdir(object):
    def __enter__(self):
        self.tempdir = Path(tempfile.mkdtemp())
        return self.tempdir

    def __exit__(self, type_, value, traceback):
        self.tempdir.rmtree()
