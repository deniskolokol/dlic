import hashlib
from dmworker.datafile import S3File
from dmworker.fileutils import md5, Archive
from dmworker.helpers import get_local_file_name, clean_working_dir
from dmworker.aws import get_key


def setup_module(module):
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()
    key = 'fixtures/dmworker/manual.ts.zip'
    key = get_key(key)
    if key is not None:
        key.delete()


def teardown_module(module):
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()
    key = 'fixtures/dmworker/manual.ts.zip'
    key = get_key(key)
    if key is not None:
        key.delete()


def test_csv():
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv'
    df = S3File(key)
    assert not df.is_compressed
    local_name = get_local_file_name(df.key)
    df.download(local_name)
    assert local_name.exists()
    assert md5(local_name) == df.etag()
    md5sum = df.etag()
    df.compress(local_name)
    zkey = df.key
    assert df.is_compressed
    clean_working_dir()
    local_name = get_local_file_name(df.key)
    df.download(local_name)
    assert local_name.exists()
    with Archive(local_name) as archive:
        data = ''.join(x for x in archive.open_member(archive.get_members()[0]))
        assert hashlib.md5(data).hexdigest() == md5sum


def test_ts():
    clean_working_dir()
    key = 'fixtures/dmworker/manual.ts'
    df = S3File(key)
    assert not df.is_compressed
    local_name = get_local_file_name(df.key)
    df.download(local_name)
    assert local_name.exists()
    assert md5(local_name) == df.etag()


def test_csv_zip():
    clean_working_dir()
    key = 'fixtures/dmworker/iris-zip.zip'
    df = S3File(key)
    assert df.is_compressed
    assert key == df.get_compressed_name()
    local_name = get_local_file_name(df.key)
    df.download(local_name)
    assert local_name.exists()
    assert md5(local_name) == df.etag()
    df.compress(local_name)
    assert key == df.key
    assert df.is_compressed


def test_ts_gz():
    clean_working_dir()
    key = 'fixtures/dmworker/manual-gz.ts.gz'
    df = S3File(key)
    assert df.is_compressed
    assert key == df.get_compressed_name()
    local_name = get_local_file_name(df.key)
    df.download(local_name)
    assert local_name.exists()
    assert md5(local_name) == df.etag()
    df.compress(local_name)
    assert key == df.key
    assert df.is_compressed
    df.swap_to_zip()
    assert key == df.key
    assert df.is_compressed


def test_swap_to_zip():
    clean_working_dir()
    key = 'fixtures/dmworker/manual.ts.zip'
    key = get_key(key)
    if key is not None:
        key.delete()
    key = 'fixtures/dmworker/manual.ts'
    df = S3File(key)
    assert not df.is_compressed
    df.swap_to_zip()
    assert df._key is None
