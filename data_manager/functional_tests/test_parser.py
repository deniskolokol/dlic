import os
import mock
from dmworker.app import settings
from dmworker import parser
from dmworker.helpers import clean_working_dir
from dmworker.aws import get_key


notify = mock.MagicMock()

def setup_module(module):
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()
    key = 'fixtures/dmworker/invalid.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()


def teardown_module(module):
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()
    key = 'fixtures/dmworker/invalid.csv.zip'
    key = get_key(key)
    if key is not None:
        key.delete()


def test_csv():
    clean_working_dir()
    key = 'fixtures/dmworker/iris.csv'
    meta = parser.run(key, notify)
    assert meta == {
        'data_type': 'GENERAL',
        'version': 3,
        'key': 'fixtures/dmworker/iris.csv.zip',
        'size': 18750,
        'num_columns': 5,
        'data_rows': 150,
        'invalid_rows': 0,
        'empty_rows': 0,
        'delimeter': '\\s+',
        'with_header': False,
        'dtypes': ['f', 'f', 'f', 'f', 'i'],
        'classes': [[], [], [], [], []],
        'uniques_per_col': [35, 23, 43, 22, 3],
        'locked': [True, True, True, True, False],
        'histogram': [[9, 23, 14, 27, 22, 20, 18, 6, 5, 6],
                      [4, 7, 22, 24, 38, 31, 9, 11, 2, 2],
                      [37, 13, 0, 3, 8, 26, 29, 18, 11, 5],
                      [41, 8, 1, 7, 8, 33, 6, 23, 9, 14],
                      [50, 50, 50]],
        'bins': [[4.3, 4.66, 5.02, 5.38, 5.74, 6.1, 6.46, 6.82, 7.18, 7.54, 7.9],
                 [2, 2.24, 2.48, 2.72, 2.96, 3.2, 3.44, 3.68, 3.92, 4.16, 4.4],
                 [1, 1.59, 2.18, 2.77, 3.36, 3.95, 4.54, 5.13, 5.72, 6.31, 6.9],
                 [0.1, 0.34, 0.58, 0.82, 1.06, 1.3, 1.54, 1.78, 2.02, 2.26, 2.5],
                 [0, 0.666667, 1.33333, 2]],
        'last_column_info': {
            'distrib': {'1': 0.333333, '0': 0.333333, '2': 0.333333},
            'classes': {'0': 50, '2': 50, '1': 50}, 
            'min': 0,
            'max': 2,
            'unique': 3
            },
        'names': ['1', '2', '3', '4', '5'],
        'mean': [5.84333, 3.054, 3.75867, 1.19867, 1],
        'stdev': [0.828066, 0.433594, 1.76442, 0.763161, 0.819232],
        'max': [7.9, 4.4, 6.9, 2.5, 2],
        'min': [4.3, 2, 1, 0.1, 0]
        }

    stat = os.stat(settings.DMWORKER_WORKING_DIR.child(key.replace('/', '_')))
    get_key(meta['key']).delete()
    meta = parser.run(key, notify)
    assert meta == {
        'data_type': 'GENERAL',
        'version': 3,
        'key': 'fixtures/dmworker/iris.csv.zip',
        'size': 18750,
        'num_columns': 5,
        'data_rows': 150,
        'invalid_rows': 0,
        'empty_rows': 0,
        'delimeter': '\\s+',
        'with_header': False,
        'dtypes': ['f', 'f', 'f', 'f', 'i'],
        'classes': [[], [], [], [], []],
        'uniques_per_col': [35, 23, 43, 22, 3],
        'locked': [True, True, True, True, False],
        'histogram': [[9, 23, 14, 27, 22, 20, 18, 6, 5, 6],
                      [4, 7, 22, 24, 38, 31, 9, 11, 2, 2],
                      [37, 13, 0, 3, 8, 26, 29, 18, 11, 5],
                      [41, 8, 1, 7, 8, 33, 6, 23, 9, 14],
                      [50, 50, 50]],
        'bins': [[4.3, 4.66, 5.02, 5.38, 5.74, 6.1, 6.46, 6.82, 7.18, 7.54, 7.9],
                 [2, 2.24, 2.48, 2.72, 2.96, 3.2, 3.44, 3.68, 3.92, 4.16, 4.4],
                 [1, 1.59, 2.18, 2.77, 3.36, 3.95, 4.54, 5.13, 5.72, 6.31, 6.9],
                 [0.1, 0.34, 0.58, 0.82, 1.06, 1.3, 1.54, 1.78, 2.02, 2.26, 2.5],
                 [0, 0.666667, 1.33333, 2]],
        'last_column_info': {
            'distrib': {'1': 0.333333, '0': 0.333333, '2': 0.333333},
            'classes': {'1': 50, '0': 50, '2': 50},
            'unique': 3,
            'max': 2,
            'min': 0},
        'names': ['1', '2', '3', '4', '5'],
        'mean': [5.84333, 3.054, 3.75867, 1.19867, 1],
        'stdev': [0.828066, 0.433594, 1.76442, 0.763161, 0.819232],
        'max': [7.9, 4.4, 6.9, 2.5, 2],
        'min': [4.3, 2, 1, 0.1, 0]
        }

    stat2 = os.stat(settings.DMWORKER_WORKING_DIR.child(key.replace('/', '_')))
    assert stat.st_ctime == stat2.st_ctime
    get_key(meta['key']).delete()
    meta = parser.run(key, notify)
    assert meta == {
        'data_type': 'GENERAL',
        'version': 3,
        'key': 'fixtures/dmworker/iris.csv.zip',
        'size': 18750,
        'num_columns': 5,
        'data_rows': 150,
        'invalid_rows': 0,
        'empty_rows': 0,
        'delimeter': '\\s+',
        'with_header': False,
        'dtypes': ['f', 'f', 'f', 'f', 'i'],
        'classes': [[], [], [], [], []],
        'uniques_per_col': [35, 23, 43, 22, 3],
        'locked': [True, True, True, True, False],
        'histogram': [[9, 23, 14, 27, 22, 20, 18, 6, 5, 6],
                      [4, 7, 22, 24, 38, 31, 9, 11, 2, 2],
                      [37, 13, 0, 3, 8, 26, 29, 18, 11, 5],
                      [41, 8, 1, 7, 8, 33, 6, 23, 9, 14],
                      [50, 50, 50]],
        'bins': [[4.3, 4.66, 5.02, 5.38, 5.74, 6.1, 6.46, 6.82, 7.18, 7.54, 7.9],
                 [2, 2.24, 2.48, 2.72, 2.96, 3.2, 3.44, 3.68, 3.92, 4.16, 4.4],
                 [1, 1.59, 2.18, 2.77, 3.36, 3.95, 4.54, 5.13, 5.72, 6.31, 6.9],
                 [0.1, 0.34, 0.58, 0.82, 1.06, 1.3, 1.54, 1.78, 2.02, 2.26, 2.5],
                 [0, 0.666667, 1.33333, 2]],
        'last_column_info': {
            'distrib': {'0': 0.333333, '2': 0.333333, '1': 0.333333},
            'classes': {'0': 50, '2': 50, '1': 50}, 
            'unique': 3,
            'min': 0,
            'max': 2
            },
        'names': ['1', '2', '3', '4', '5'],
        'mean': [5.84333, 3.054, 3.75867, 1.19867, 1],
        'stdev': [0.828066, 0.433594, 1.76442, 0.763161, 0.819232],
        'max': [7.9, 4.4, 6.9, 2.5, 2],
        'min': [4.3, 2, 1, 0.1, 0]
        }

def test_csv_text_labels():
    clean_working_dir()
    key = 'fixtures/dmworker/invalid.csv'
    meta = parser.run(key, notify)
    assert meta == {
        'size': 85,
        'data_rows': 3,
        'uniques_per_col': [3, 3, 1, 3],
        'key': 'fixtures/dmworker/invalid.csv.zip',
        'data_type': 'GENERAL',
        'invalid_rows': 0,
        'version': 3,
        'histogram': [[1, 1, 1], [1, 1, 1], [3], [1, 1, 1]],
        'bins': [[0, 0.666667, 1.33333, 2], [0.1, 0.333333, 0.566667, 0.8], [0.11, 0.11], [0, 0.666667, 1.33333, 2]],
        'dtypes': ['S', 'f', 'f', 'S'],
        'classes': [['A', 'M', 'U'], [], [], ['class1', 'class2', 'class3']],
        'last_column_info': {
            'distrib': {'class2': 0.333333, 'class3': 0.333333, 'class1': 0.333333},
            'classes': {'class2': 1, 'class3': 1, 'class1': 1},
            'unique': 3,
            'max': 2,
            'min': 0},
        'names': ['column1', 'column2', 'column3', 'column4'],
        'delimeter': '\\s+',
        'num_columns': 4,
        'locked': [True, True, True, True],
        'with_header': True,
        'empty_rows': 0,
        'mean': [None, 0.466667, 0.11, None],
        'stdev': [None, 0.351188, 0, None],
        'max': [None, 0.8, 0.11, None],
        'min': [None, 0.1, 0.11, None]
        }
