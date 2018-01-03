import logging
import datetime
import ConfigParser
import io
import json
import cStringIO
import gzip
import collections
import random
import string
import redis
from django.conf import settings
from django.core.cache import cache


if getattr(settings, 'LOCAL_SETUP', False):
    from . import s3_local as connection
    from . import s3_local as s3_key
    from .s3_local import S3ResponseError, S3DataError
else:
    from boto.s3 import key as s3_key
    from boto.s3 import connection
    from boto.exception import S3ResponseError, S3DataError


class FileBackendError(Exception):
    pass


class ExcludeNotAllowedHost(logging.Filter):
    def filter(self, record):
        try:
            return 'Invalid HTTP_HOST header' not in record.exc_info[1].message
        except:
            return True


class RequireTestRunFalse(logging.Filter):
    def filter(self, record):
        try:
            return not settings.TEST_RUN
        except:
            return True


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def make_random_str(size=8):
    return ''.join([random.choice(string.digits + string.letters)
                    for _ in range(0, size)])


def update_config(data, section, key, value):
    config = ConfigParser.ConfigParser()
    config.readfp(io.BytesIO(str(data)))
    config.set(str(section), str(key), str(value))
    new_config = io.BytesIO()
    config.write(new_config)
    new_config.seek(0)
    return unicode(new_config.read()).replace(' ', '') \
        .replace('\n\n', '\n').strip()


def get_modeldata(s3_data):
    try:
        s3_conn = connection.S3Connection(settings.AWS_ACCESS_KEY,
                                          settings.AWS_SECRET_KEY)
        key = s3_key.Key(s3_conn.get_bucket(settings.S3_BUCKET))
        key.key = s3_data
        data = key.get_contents_as_string()
    except (S3ResponseError, S3DataError):
        raise FileBackendError()
    if s3_data.endswith('.gz'):
        data = gzip_to_str(data)
    return json.loads(data)


def gzip_to_str(data):
    arch = cStringIO.StringIO(data)
    f = gzip.GzipFile(fileobj=arch, mode='rb')
    data = f.read()
    f.close()
    return data


def deep_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = deep_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def build_key(user_id, filename, prefix="uploads"):
    return "{0}/{1}/{2}/{3}".format(prefix, user_id,
                                    make_random_str(), filename)


def upload_data_to_s3(key, fp):
    s3_conn = connection.S3Connection(settings.AWS_ACCESS_KEY,
                                      settings.AWS_SECRET_KEY)
    k = s3_key.Key(s3_conn.get_bucket(settings.S3_BUCKET))
    k.key = key
    k.set_contents_from_file(fp)


def sign_s3_get(key):
    rval = cache.get('signed_url:%s:%s' % (settings.S3_BUCKET, key))
    if rval is None:
        life_time = 3600
        s3_conn = connection.S3Connection(settings.AWS_ACCESS_KEY,
                                          settings.AWS_SECRET_KEY)
        bkey = s3_key.Key(s3_conn.get_bucket(settings.S3_BUCKET))
        bkey.key = key
        rval = bkey.generate_url(life_time, query_auth=True, force_http=True)
        cache.set('signed_url:%s:%s' % (settings.S3_BUCKET, key),
                  rval, life_time - 60)
    return rval


def redis_publish(channel, data):
    rcon = redis.StrictRedis(host=settings.REDIS_HOST,
                             port=int(settings.REDIS_PORT),
                             db=int(settings.REDIS_DB),
                             password=settings.REDIS_PASSWORD)
    rcon.publish(channel, data)


def build_url(location):
    return '{}{}'.format(settings.DMWORKER_CALLBACK_URL, location)
