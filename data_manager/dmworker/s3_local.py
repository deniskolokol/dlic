import hashlib
from unipath import Path

from .app import settings


class S3Bucket(object):
    def __init__(self, name):
        self.name = name

    def get_key(self, key):
        k = Key(self, key=key)
        if k.path.exists():
            return k
        return None


class S3Connection(object):
    def __init__(self, access_key, secret_key):
        self._access_key = access_key
        self._secret_key = secret_key

    def get_bucket(self, name):
        return S3Bucket(name)


class Key(object):
    def __init__(self, bucket, key=None):
        self.bucket = bucket
        self.key = key

    @property
    def path(self):
        return settings.S3_ROOT.child(self.bucket.name,
                                      *self.key.strip('/').split('/'))

    @property
    def etag(self):
        return fp_md5(self.path)

    def delete(self):
        self.path.remove()

    def _mkdir(self):
        self.path.parent.mkdir(parents=True)

    def get_contents_to_filename(self, local_file, *args, **kwargs):
        self.path.copy(local_file)

    def set_contents_from_filename(self, local_file, *args, **kwargs):
        self._mkdir()
        Path(local_file).copy(self.path)

    def set_contents_from_file(self, fp, *args, **kwargs):
        self._mkdir()
        with open(self.path, 'wb') as f:
            f.write(fp.read())

    def get_contents_as_string(self):
        with open(self.path, 'r') as f:
            data = f.read()
        return data

    def set_contents_from_string(self, data):
        self._mkdir()
        with open(self.path, 'wb') as f:
            f.write(data)
        return len(data)


class S3DataError(Exception):
    pass


class S3ResponseError(Exception):
    pass


def fp_md5(file_, blocksize=65536):
    with open(file_) as f:
        hasher = hashlib.md5()
        buf = f.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(blocksize)
        return hasher.hexdigest()
