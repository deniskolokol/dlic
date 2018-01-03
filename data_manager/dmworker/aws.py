from .app import settings
from .exception import InternalException


if getattr(settings, 'LOCAL_SETUP', False):
    from .s3_local import S3Connection, Key
else:
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key


def get_bucket():
    conn = S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
    return conn.get_bucket(settings.AWS_S3_BUCKET)


def get_key(key):
    return get_bucket().get_key(key)


def delete_key(key):
    key = get_key(key)
    if key is None:
        return
    key.delete()


def create_key(key):
    k = Key(get_bucket())
    k.key = key
    return k


def print_progress(done, total):
    if total > 1024*1024:
        print "progress: {0}MB/{1}MB ({2}%)".format(done/1024/1024,
                                                    total/1024/1024,
                                                    int(done*100.0/total))
    else:
        print "progress: {0}/{1} ({2}%)".format(done, total,
                                                int(done*100.0/total))


def save_to_file(key, local_file, interactive=False):
    if not isinstance(key, Key):
        key = get_key(key)
        if key is None:
            raise InternalException('S3 key doesn\'t exists.')
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
            raise InternalException('S3 already has this key.')
    if interactive:
        k.set_contents_from_filename(local_file, cb=print_progress, num_cb=11)
    else:
        k.set_contents_from_filename(local_file)
    return k
