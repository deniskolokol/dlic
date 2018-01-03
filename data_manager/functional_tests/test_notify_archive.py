import mock
import pytest
import zipfile
import tarfile
from dmworker.parser import parse, parse_archive, global_notify
from dmworker.exception import InvalidDataFile
from dmworker.fileutils import InvalidArchive
from dmworker.fileutils import tempdir, TempFile, Archive, cwd
from tests.test_parser import gen_data


def test_notify_archive_image_valid():
    data = gen_data()
    log = """
    Image dataset unpacked. Parsing...
    5 images found.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        files = [
            td.child('class1', 'f1.jpg'),
            td.child('class1', 'f2.JPG'),
            td.child('class2', 'f1.jpg'),
            td.child('class2', 'f2.bMp'),
            td.child('class2', 'f4jpg.Jpeg'),
            td.child('class3', 'test.txt'),
        ]
        for f in (files):
            f = open(f, 'w')
            f.write(data)
            f.close()
        with TempFile(suffix='.zip') as fname:
            with zipfile.ZipFile(fname, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.write(f)
            with global_notify(notify):
                parse_archive(Archive(fname))
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_notify_archive_ts_valid():
    data = gen_data()
    log = """
    Image dataset unpacked. Parsing...
    Timeseries data .//class3/test.ts unpacked. Parsing...
    First timestep has 3 inputs and 2 outputs. Applying this requirement to the entire file."""
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        files = [
            td.child('class1', 'f1.jpg'),
            td.child('class1', 'f2.JPG'),
            td.child('class2', 'f1.jpg'),
            td.child('class2', 'f2.bMp'),
            td.child('class2', 'f4jpg.Jpeg'),
            td.child('class3', 'test.ts'),
            td.child('f1.jpeg'),
        ]
        for f in (files):
            f = open(f, 'w')
            f.write(data)
            f.close()
        with open(td.child('class3', 'test.ts'), 'w') as f:
            f.write('1,2,3|0,1; 2.3,4,1|0,1; 1.1, 0., 0.0|1,0\n\n2,2,2|0,1;')
        with TempFile(suffix='.tar.gz') as fname:
            with tarfile.open(fname, 'w:gz') as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.add(f)
            with global_notify(notify):
                parse_archive(Archive(fname))
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_notify_archive_csv_valid():
    data = gen_data()
    log = """
    Image dataset unpacked. Parsing...
    CSV file .//1.csv unpacked.
    Parsing CSV with whitespace (tab) as delimiter.
    Found 3 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset appears to have a header.
    Found 2 samples."""
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        files = [
            td.child('class1', 'f1.jpg'),
            td.child('class1', 'f2.JPG'),
            td.child('class2', 'f1.jpg'),
            td.child('class2', 'f2.bMp'),
            td.child('class2', 'f4jpg.Jpeg'),
            td.child('class3', 'test.txt'),
            td.child('1.csv'),
        ]
        for f in (files):
            f = open(f, 'w')
            f.write(data)
            f.close()
        with open(td.child('1.csv'), 'w') as f:
            f.write('one two free\r1 2 3\r4 5 6')
        with TempFile(suffix='.tar.bz2') as fname:
            with tarfile.open(fname, 'w:bz2') as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.add(f)
            with global_notify(notify):
                parse_archive(Archive(fname))
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_notify_data_invalid():
    data = gen_data()
    log = """
    Image dataset unpacked. Parsing...
    This file doesn't contain a supported data format."""
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        files = [
            td.child('class3', 'test.txt'),
            td.child('1.jpg'),
        ]
        for f in (files):
            f = open(f, 'w')
            f.write(data)
            f.close()
        with TempFile(suffix='.tar.bz2') as fname:
            with tarfile.open(fname, 'w:bz2') as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.add(f)
            with global_notify(notify):
                with pytest.raises(InvalidDataFile):
                    parse_archive(Archive(fname))
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_notify_archive_invalid():
    data = 'thequickbrownfoxjumpsoverthelazydog'
    log = 'Unknown file format.'
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.foo') as foo:
        with global_notify(notify):
            with pytest.raises(InvalidArchive):
                parse(foo)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_notify_archive_image_skipped():
    data = gen_data()
    log = """
    Image dataset unpacked. Parsing...
    8 images found.
    Skipped 3 images with leading dot or without class.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class2').child('.class22').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        files = [
            td.child('class1', 'f1.jpg'),
            td.child('class1', 'f2.JPG'),
            td.child('class2', 'f1.jpg'),
            td.child('class2', '.f1.jpg'),
            td.child('class2', 'f2.bMp'),
            td.child('class2', '.class22', 'ff2.jpg'),
            td.child('class2', 'f4jpg.Jpeg'),
            td.child('class3', 'test.txt'),
            td.child('f1.jpeg'),
        ]
        for f in (files):
            f = open(f, 'w')
            f.write(data)
            f.close()
        with TempFile(suffix='.zip') as fname:
            with zipfile.ZipFile(fname, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.write(f)
            with global_notify(notify):
                parse_archive(Archive(fname))
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called
