import zipfile
from .app import log, settings
from .fileutils import zip_write, TempFile
from . import aws


class S3File(object):

    def __init__(self, key):
        self.key = key
        self._key = aws.get_key(self.key)
        self.is_uploaded = self.exists()
        self.is_compressed = True
        if self.key.lower().endswith(settings.DMWORKER_COMPRESS_EXT):
            self.is_compressed = False

    def exists(self):
        return self._key is not None

    def etag(self):
        return self._key.etag.strip('"')

    def get_compressed_name(self):
        if self.key.lower().endswith(settings.DMWORKER_COMPRESS_EXT):
            return self.key + '.zip'
        else:
            return self.key

    def swap_to_zip(self, aws_key=None):
        if self.is_compressed is False:
            self.key = self.get_compressed_name()
            if aws_key is None:
                self._key = aws.get_key(self.key)
            else:
                self._key = aws_key
            self.is_compressed = True
        else:
            log.error('Can\'t swap to zip because is_compressed == True')

    def download(self, file_path):
        aws.save_to_file(self.key, file_path, interactive=True)

    def compress(self, local_copy):
        if self.is_compressed:
            return
        with TempFile() as zip_file:
            if not zipfile.is_zipfile(local_copy):
                name = self.key.strip('/').split('/')[-1]
                local_copy = zip_write(zip_file, local_copy, name)
            zkey = self.get_compressed_name()
            aws.save_to_s3(local_copy, zkey, interactive=True)
        self.swap_to_zip(zkey)

    def upload(self, local_copy):
        aws.save_to_s3(local_copy, self.key, interactive=True)
