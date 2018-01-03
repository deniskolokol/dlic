import string
import random
import zipfile
import tarfile
import pytest
import mock
from dmworker.fileutils import tempdir, TempFile, Archive, cwd
from dmworker.parser import parse_archive, parse, set_notify
from dmworker.exception import InvalidDataFile


set_notify(mock.MagicMock())


def gen_string(size=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in xrange(size))


def gen_data(string_size=10, num_lines=20):
    return '\n'.join(gen_string(string_size) for _ in xrange(num_lines))


def test_parse_img_archive():
    data = gen_data()
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
            meta = parse_archive(Archive(fname))
            assert meta == {
                'data_type': 'IMAGES',
                'classes': {'class1': 2, 'class2': 3}
            }


def test_parse_nested_img_archive():
    data = gen_data()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('class3').mkdir()
        td.child('class4').mkdir()
        td.child('class1').child('class1B').mkdir()
        td.child('class2').child('class2B').mkdir()
        td.child('class2').child('class2B').child('class2Bi').mkdir()
        td.child('class3').child('class3B').mkdir()
        files = [
            td.child('class1', 'f1.jpg'),
            td.child('class1', 'f1a.jpg'),
            td.child('class1').child('class1B', 'f2.jpg'),
            td.child('class2', 'f5.jpg'),
            td.child('class2').child('class2B').child('class2Bi', 'f3.jpg'),
            td.child('class3', 'f4.jpg'),
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
            meta = parse_archive(Archive(fname))
            assert meta == {
                'data_type': 'IMAGES',
                'classes': {
                    'class1': 2,
                    'class1/class1B': 1,
                    'class2': 1,
                    'class2/class2B/class2Bi':1,
                    'class3': 1
                }
            }


def test_parse_dot_img_archive():
    data = gen_data()
    with tempdir() as td:
        td.child('class1').mkdir()
        td.child('class2').mkdir()
        td.child('.class3').mkdir()
        td.child('class4').mkdir()
        td.child('class1').child('class1B').mkdir()
        td.child('class2').child('.class2B').mkdir()
        td.child('class2').child('.class2B').child('class2Bi').mkdir()
        td.child('.class3').child('class3B').mkdir()
        files = [
            td.child('class1', '.f1.jpg'),
            td.child('class1', 'f1a.jpg'),
            td.child('class1').child('class1B', 'f2.jpg'),
            td.child('class2', 'f5.jpg'),
            td.child('class2').child('.class2B').child('class2Bi', 'f3.jpg'),
            td.child('.class3', 'f4.jpg'),
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
            meta = parse_archive(Archive(fname))
            assert meta == {
                'data_type': 'IMAGES',
                'classes': {
                    'class1': 1,
                    'class1/class1B': 1,
                    'class2': 1,
                }
            }


def test_parse_ts_archive():
    data = gen_data()
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
            meta = parse_archive(Archive(fname))
            assert meta == {
                'data_type': 'TIMESERIES',
                'data_rows': 2,
                'empty_rows': 1,
                'min_timesteps': 1,
                'max_timesteps': 3,
                'input_size': 3,
                'output_size': 2,
                'classes': {'0': 1, '1': 3},
                'binary_input': False,
                'binary_output': True,
                'archive_path': './/class3/test.ts'
            }


def test_parse_csv_archive():
    data = gen_data()
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
            f.write('one two free\r1 2 3\r4 5 6\r7 8 9\r1 2 3\r3 4 5\r4 5 5\r1 2 3\r0 9 9\r0 8 3\r3 3 3\r')
        with TempFile(suffix='.tar.bz2') as fname:
            with tarfile.open(fname, 'w:bz2') as z:
                with cwd(td):
                    for f in (files):
                        f = f.replace(td, './')
                        z.add(f)
            meta = parse_archive(Archive(fname))
            assert meta == {
                'version': 3,
                'size': 73,
                'archive_path': './/1.csv',
                'data_rows': 10,
                'uniques_per_col': [5, 6, 4],
                'data_type': 'GENERAL',
                'invalid_rows': 0,
                'histogram': [[5, 0, 4, 0, 1], [4, 1, 2, 0, 0, 3], [5, 2, 1, 2]],
                'bins': [[0, 1.4, 2.8, 4.2, 5.6, 7], [2, 3.16667, 4.33333, 5.5, 6.66667, 7.83333, 9], [3, 4.5, 6, 7.5, 9]],
                'dtypes': ['i', 'i', 'i'],
                'classes': [[], [], []],
                'last_column_info': {
                    'classes': {'9': 2, '3': 5, '5': 2, '6': 1},
                    'distrib': {'9': 0.2, '3': 0.5, '5': 0.2, '6': 0.1},
                    'min': 3,
                    'max': 9,
                    'unique': 4},
                'names': ['one', 'two', 'free'],
                'delimeter': '\s+',
                'num_columns': 3,
                'locked': [False, False, False],
                'with_header': True,
                'empty_rows': 0,
                'mean': [2.4, 4.8, 4.9],
                'stdev': [2.22111, 2.69979, 2.42441],
                'max': [7, 9, 9],
                'min': [0, 2, 3]
                }


def test_invalid_archive():
    data = gen_data()
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
            with pytest.raises(InvalidDataFile) as excinfo:
                parse_archive(Archive(fname))
    assert excinfo.value.message == 'This file doesn\'t contain a supported data format.'


def test_parse_with_archive():
    data = gen_data()
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
            meta = parse(fname)
            assert meta == {
                'data_type': 'IMAGES',
                'classes': {'class1': 2, 'class2': 3}
            }


def test_parse_with_csv():
    with TempFile('1,2,3\r\n2,3,4', suffix='.csv') as csv:
        meta = parse(csv)
    assert meta == {
        'data_type': 'GENERAL',
        'version': 3,
        'size': 12,
        'data_rows': 2,
        'empty_rows': 0,
        'invalid_rows': 0,
        'num_columns': 3,
        'delimeter': '\s*,\s*',
        'with_header': False,
        'last_column_info': {
            'classes': {'3': 1, '4': 1},
            'distrib': {'3': 0.5, '4': 0.5},
            'max': 4.,
            'min': 3.,
            'unique': 2,
        },
        'histogram': [[1, 1], [1, 1], [1, 1]],
        'bins': [[1.0, 1.5, 2.0], [2.0, 2.5, 3.0], [3.0, 3.5, 4.0]],
        'uniques_per_col': [2, 2, 2],
        'classes': [[], [], []],
        'dtypes': ['i', 'i', 'i'],
        'locked': [False, False, False],
        'names': ['1', '2', '3'],
        'mean': [1.5, 2.5, 3.5],
        'stdev': [0.707107, 0.707107, 0.707107],
        'max': [2, 3, 4],
        'min': [1, 2, 3]
    }


def test_parse_with_csv_zip():
    with TempFile(suffix='.zip') as t:
        with zipfile.ZipFile(t, 'w') as z:
            z.writestr('test.csv', '1 2 3\n2 3 4')
        meta = parse(t)
    assert meta == {
        'data_type': 'GENERAL',
        'version': 3,
        'size': 12,
        'data_rows': 2,
        'empty_rows': 0,
        'invalid_rows': 0,
        'num_columns': 3,
        'delimeter': '\s+',
        'with_header': False,
        'archive_path': 'test.csv',
        'last_column_info': {
            'classes': {'3': 1, '4': 1},
            'distrib': {'3': 0.5, '4': 0.5},
            'max': 4.,
            'min': 3.,
            'unique': 2,
        },
        'histogram': [[1, 1], [1, 1], [1, 1]],
        'bins': [[1.0, 1.5, 2.0], [2.0, 2.5, 3.0], [3.0, 3.5, 4.0]],
        'uniques_per_col': [2, 2, 2],
        'classes': [[], [], []],
        'dtypes': ['i', 'i', 'i'],
        'locked': [False, False, False],
        'names': ['1', '2', '3'],
        'mean': [1.5, 2.5, 3.5],
        'stdev': [0.707107, 0.707107, 0.707107],
        'max': [2, 3, 4],
        'min': [1, 2, 3]
    }


def test_parse_with_ts():
    with TempFile('1,2,3|1, 0;2,3,4|1,0', suffix='.ts') as ts:
        meta = parse(ts)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 1,
        'empty_rows': 0,
        'min_timesteps': 2,
        'max_timesteps': 2,
        'classes': {'0': 2},
        'binary_input': False,
        'binary_output': True,
        'input_size': 3,
        'output_size': 2
    }
