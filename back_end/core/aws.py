import os
import json
import string
import time
import gzip
import StringIO
from random import choice
from boto import log as boto_log
from . import get_logger
from .conf import settings
from .misc import NPArrayEncoder, str_to_gzip, gzip_to_str, fp_md5
from .exception import AWSError


if getattr(settings, 'LOCAL_SETUP', False):
    from .s3_local import S3Connection, Key
else:
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key


log = get_logger('ersatz.aws')
boto_log.setLevel(settings.LOGLEVEL)


class S3Key(object):
    def __init__(self, key):
        self.key = key

    def download(self, local_filename):
        log.debug('Downloading %s from S3.' % self.key)
        local_filename.ancestor(1).mkdir(parents=True)
        save_to_file(self.key, local_filename, interactive=True)

    def get(self):
        key = get_key(self.key)
        local = os.path.join(settings.S3_CACHEDIR, self.key.strip('/')) #strip leading /

        if os.path.exists(local) and fp_md5(local) == key.etag.strip('"'):
            log.debug('Using cached version of %s.' % self.key)
        else:
            self.download(local)
        return local

    def get_file(self):
        local = self.get()

        if local.endswith('.gz'):
            fil = gzip.GzipFile(local, mode='rb')
        else:
            fil = open(local, 'r')

        return fil

def upload_modeldata(data, load_file, model_id):
    if not isinstance(data, str):
        data = json.dumps(data, cls=NPArrayEncoder)
    data = str_to_gzip(data)
    if load_file:
        s3_data = save_modeldata_to_filename(load_file, data)
    else:
        s3_data = save_modeldata(model_id, '00', data, suffix='.json.gz')
    return s3_data


def get_key(key):
    if key is None or key == '':
        raise AWSError
    conn = S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
    bucket = conn.get_bucket(settings.S3_BUCKET)
    return bucket.get_key(key)


def create_key(key):
    conn = S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
    bucket = conn.get_bucket(settings.S3_BUCKET)
    k = Key(bucket)
    k.key = key
    return k


def save_modeldata_to_filename(s3_filename, modeldata):
    k = create_key(s3_filename)
    if isinstance(modeldata, file):
        bts = k.set_contents_from_file(modeldata)
    else:
        if not isinstance(modeldata, str):
            modeldata = json.dumps(modeldata, cls=NPArrayEncoder)
        start_time = time.time()
        bts = k.set_contents_from_string(modeldata)
        log.debug('S3 uploading time: %s' % (time.time() - start_time, ))
    if bts == len(modeldata):
        log.debug('Saved %s Mb to S3.' % round(bts / 1024. / 1024., 2))
        return k.key
    else:
        log.critical('Number of saved bytes not equal data length')
        return None


def save_modeldata(model_id, iteration, modeldata, suffix='.json'):
    prefix = ''.join([choice(string.digits + string.letters) for i in range(0, 8)])
    s3_filename = '/modeldata/'  + str(model_id) + '/' + \
            str(iteration) + '_' + prefix + suffix
    return save_modeldata_to_filename(s3_filename, modeldata)


def get_data(key):
    k = get_key(key)
    if k is None:
        raise AWSError
    data = k.get_contents_as_string()
    if key.endswith('.gz'):
        data = gzip_to_str(data)
    return data


def print_progress(done, total):
    if total > 1024*1024:
        print "progress: {0}MB/{1}MB ({2}%)".format(done/1024/1024,
                                                    total/1024/1024,
                                                    int(done*100.0/total))
    else:
        print "progress: {0}/{1} ({2}%)".format(done, total, int(done*100.0/total))


def save_to_file(key, local_file, interactive=False):
    if not isinstance(key, Key):
        key = get_key(key)
        if key is None:
            raise AWSError('S3 key doesn\'t exists.')
    if interactive:
        key.get_contents_to_filename(local_file, cb=print_progress, num_cb=11)
    else:
        key.get_contents_to_filename(local_file)


def save_to_s3(local_file, key, rewrite=False, interactive=False):
    if not isinstance(key, Key):
        k = get_key(key)
        if k is None:
            k = create_key(key)
        elif not rewrite:
            raise AWSError('S3 already has this key.')
    if interactive:
        k.set_contents_from_filename(local_file, cb=print_progress, num_cb=11)
    else:
        k.set_contents_from_filename(local_file)


def get_list_files():
    conn = S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
    bucket = conn.get_bucket(settings.S3_BUCKET)
    return bucket.list()


def save_as_s3_file(rval, s3_key):
    gz = StringIO.StringIO()
    f = gzip.GzipFile(fileobj=gz, mode='w')
    f.write(rval)
    f.close()
    save_modeldata_to_filename(s3_key, gz.getvalue())
    return s3_key
