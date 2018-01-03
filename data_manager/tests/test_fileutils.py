import os
import sys
import gzip
import bz2
import tarfile
import zipfile
import string
import random
import pytest
import subprocess
from unipath import Path
from dmworker.app import settings
from dmworker.fileutils import (md5, open_file, open_gz, open_bz,
                                TempFile, zip_write, cwd, Archive,
                                tempdir, InvalidArchive)
from dmworker.helpers import clean_working_dir, get_local_file_name


def gen_string(size=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in xrange(size))


def gen_data(string_size=10, num_lines=20):
    return '\n'.join(gen_string(string_size) for _ in xrange(num_lines))


@pytest.mark.skipif('linux' not in sys.platform,
                    reason="requires linux for md5sum")
def test_md5():
    with TempFile(gen_data()) as fname:
        m1 = md5(fname)
        m2 = subprocess.check_output(['md5sum', fname]).split(None, 1)[0]
        assert m1 == m2


def test_open_file():
    data = gen_data()
    with TempFile(data) as fname:
        assert data.split('\n') == list(open_file(fname))
    with TempFile(data + '\n') as fname:
        assert data.split('\n') == list(open_file(fname))


def test_open_gz():
    data = gen_data()
    with TempFile() as fname:
        with gzip.open(fname, 'wb') as gz:
            gz.write(data)
            gz.close()
        assert data.split('\n') == list(open_gz(fname))


def test_open_bz():
    data = gen_data()
    with TempFile() as fname:
        with bz2.BZ2File(fname, 'wb') as bz:
            bz.write(data)
            bz.close()
        assert data.split('\n') == list(open_bz(fname))


def test_zip_write():
    data = gen_data() + ' ' * 1000
    with TempFile(data) as fname:
        with TempFile() as zip_file:
            zip_write(zip_file, fname)
            assert os.stat(fname).st_size > os.stat(zip_file).st_size
            with zipfile.ZipFile(zip_file) as z:
                assert data == z.read(z.namelist()[0])


def test_cwd():
    init = os.path.abspath('.')
    temp_path = '/tmp/' + gen_string()
    with cwd(temp_path) as newpath:
        assert newpath == temp_path == os.path.abspath('.')
    assert init == os.path.abspath('.')
    os.rmdir(temp_path)


def test_archive_zip():
    data1 = gen_data(5, 10)
    data2 = gen_data().replace('\n', '\r')
    with TempFile(data1) as f1:
        with TempFile(data2) as f2:
            with TempFile(suffix='.zip') as fname:
                with zipfile.ZipFile(fname, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                    z.write(f1)
                    z.write(f2)
                members = None
                with Archive(fname) as archive:
                    members = archive.get_members()
                    assert sorted(members) == sorted([f.lstrip('/') for f in f1, f2])
                with Archive(fname) as archive:
                    member = archive.open_member(sorted(members)[0])
                    assert ''.join(x for x in member) == sorted(zip([f1, f2], [data1, data2]))[0][1].replace('\r', '\n')
                with Archive(fname) as archive:
                    member = archive.open_member(sorted(members)[1])
                    assert ''.join(x for x in member) == sorted(zip([f1, f2], [data1, data2]))[1][1].replace('\r', '\n')
                with Archive(fname) as archive:
                    size = archive.get_member_size(f1.lstrip('/'))
                    assert size == 59


def test_archive_tar_gz():
    data1 = gen_data(5, 10)
    data2 = gen_data()
    with TempFile(data1) as f1:
        with TempFile(data2) as f2:
            with TempFile(suffix='.tar.gz') as fname:
                with tarfile.open(fname, 'w:gz') as z:
                    z.add(f1)
                    z.add(f2)
                members = None
                with Archive(fname) as archive:
                    members = archive.get_members()
                    assert sorted(members) == sorted([f.lstrip('/') for f in f1, f2])
                with Archive(fname) as archive:
                    member = archive.open_member(sorted(members)[1])
                    assert '\n'.join(x for x in member) == sorted(zip([f1, f2], [data1, data2]))[1][1]
                with Archive(fname) as archive:
                    size = archive.get_member_size(f1.lstrip('/'))
                    assert size == 59


def test_archive_tar_bz():
    data1 = gen_data(5, 10).replace('\n', '\r')
    data2 = gen_data().replace('\n', '\r')
    with TempFile(data1) as f1:
        with TempFile(data2) as f2:
            with TempFile(suffix='.tar.bz') as fname:
                with tarfile.open(fname, 'w:bz2') as z:
                    z.add(f1)
                    z.add(f2)
                members = None
                with Archive(fname) as archive:
                    members = archive.get_members()
                    assert sorted(members) == sorted([f.lstrip('/') for f in f1, f2])
                with Archive(fname) as archive:
                    member = archive.open_member(sorted(members)[1])
                    assert '\r'.join(x for x in member) == sorted(zip([f1, f2], [data1, data2]))[1][1]
                with Archive(fname) as archive:
                    size = archive.get_member_size(f1.lstrip('/'))
                    assert size == 59


def test_archive_invalid():
    data = gen_data()
    with TempFile(data) as tf:
        with pytest.raises(InvalidArchive):
            Archive(tf)
    with TempFile(data, suffix='.zip') as tf:
        with pytest.raises(InvalidArchive):
            Archive(tf)
    with TempFile(data, suffix='.tar.bz') as tf:
        with pytest.raises(InvalidArchive):
            Archive(tf)


def test_clean_working_dir():
    def create_dir(pwd):
        pwd.child('empty_dir').mkdir()
        pwd.child('not_empty_dir').mkdir()
        pwd.child('not_empty_dir', 'deep_dir').mkdir()
        open(pwd.child('not_empty_dir', 'file1'), 'w').close()
        open(pwd.child('not_empty_dir', 'file2'), 'w').close()
        open(pwd.child('not_empty_dir', 'deep_dir', 'file5'), 'w').close()
        open(pwd.child('file3'), 'w').close()
        open(pwd.child('file4'), 'w').close()


    with tempdir() as td:
        create_dir(td)
        clean_working_dir(exclude=['not_empty_dir/deep_dir/file5'], working_dir=td)
        assert Path(td).child('not_empty_dir', 'deep_dir', 'file5').exists()
        assert len(Path(td).listdir()) == 1
    with tempdir() as td:
        create_dir(td)
        clean_working_dir(exclude=[Path(td).child('not_empty_dir', 'deep_dir', 'file5')], working_dir=td)
        assert Path(td).child('not_empty_dir', 'deep_dir', 'file5').exists()
        assert len(Path(td).listdir()) == 1
    with tempdir() as td:
        create_dir(td)
        clean_working_dir(working_dir=td)
        assert Path(td).listdir() == []
    with tempdir() as td:
        create_dir(td)
        clean_working_dir(exclude=['not_empty_dir/deep_dir/file5',
                                   'not_empty_dir/file1'], working_dir=td)
        assert Path(td).child('not_empty_dir', 'deep_dir', 'file5').exists()
        assert Path(td).child('not_empty_dir', 'file1').exists()
        assert len(Path(td).listdir()) == 1
    with tempdir() as td:
        create_dir(td)
        clean_working_dir(exclude=['file3'], working_dir=td)
        assert Path(td).child('file3').exists()
        assert len(Path(td).listdir()) == 1
    with tempdir() as td:
        create_dir(td)
        clean_working_dir(exclude=['file3'], working_dir=td)
        assert Path(td).child('file3').exists()
        assert len(Path(td).listdir()) == 1
    with pytest.raises(ValueError):
        with tempdir() as td:
            create_dir(td)
            clean_working_dir(exclude='file3', working_dir=td)


def test_get_local_file_name():
    name = get_local_file_name('/upload/test/1234/text.csv')
    assert name == settings.DMWORKER_WORKING_DIR.child('upload_test_1234_text.csv')


def test_archive_get_img_class():
    m = './/././././.1/2/3.jpg'
    assert Archive.get_img_class(m) is None
    m = './/././././1/2/3.jpg'
    assert Archive.get_img_class(m) == '1/2'
    m = '1/2/.3.jpg'
    assert Archive.get_img_class(m) is None
    m = '1/2/3.jpg'
    assert Archive.get_img_class(m) == '1/2'
    m = '.3.jpg'
    assert Archive.get_img_class(m) is None
    m = '3.jpg'
    assert Archive.get_img_class(m) is None
    m = './/3.jpg'
    assert Archive.get_img_class(m) is None
    m = './1/3.jpg'
    assert Archive.get_img_class(m) == '1'
    m = './/.././1/2/../4/./3.jpg'
    assert Archive.get_img_class(m) == '1/2/../4/.'
    m = '.1/3.jpg'
    assert Archive.get_img_class(m) is None


def test_empty_archive():
    with TempFile(suffix='.zip') as td:
        with zipfile.ZipFile(td, 'w'):
            pass
        archive = Archive(td)
        assert [] == archive.get_members()

    with TempFile(suffix='.tar.gz') as td:
        with tarfile.open(td, 'w:gz'):
            pass
        archive = Archive(td)
        assert [] == archive.get_members()


def test_zip_get_members():
    names = ['whitespace in name.jpg', '1/2/test 1.jpg', '33/a\'a.bin',
             '.test.jpg', '1/.2 3/3/test.jpg', './.1/test/test.jpg']
    with TempFile(suffix='.zip') as td:
        with zipfile.ZipFile(td, 'w') as z:
            for name in names:
                z.writestr(name, 'null')
        archive = Archive(td)
        members = archive.get_members()
    assert sorted(names) == sorted(members)
