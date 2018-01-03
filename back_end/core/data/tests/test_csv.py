import os
import cStringIO
import pytest
import numpy as np
from ersatz.aws import S3Key
from ersatz.data import csv as data_csv

# Testing on the following data:
# - filename:
# x1,     x2,     x3,     y
# 0.409,  0.796,  0.69,   4
# 0.917,  0.911,  0.532,  1
# 0.276,  0.757,  0.927,  2
# 0.274,  0.055,  0.664,  6
# 22,     7,      0,      1
# 51,     48,     38,     1
# 69,     40,     16,     0
# 1,     28,      98,     1
#
# - filename_merge:
# x1,   x2,    x3,    y
# 2,    29,    30,    1
# 5,    50,    46,    0
# 1,    7,     89,    1
# 0,    10,    92,    9
# 4,    11,    8,     1
# 3,    92,    1,     0
#
# - filename_text:
# x1,     x2,        x3,             x4,  y
# 2000,   Mercury,   0.146851813,    4,   in
# 3400,   Mars,      0.8655614457,   1,   in
# 120,    Venus,     0.1147525953,   2,   out
# 800,    Earth,     0.2786844389,   6,   in
# 2100,   Jupiter,   0.8940182284,   1,   N/A
# 2200,   ,          0.7818682764,   1,   in
# 200,    Mars,      0.4230423784,   0,   N/A
# 18000,  Jupiter,   0.8164396221,   1,   out

LINES = "x1,x2,x3,y\n0.409,0.796,0.69,4\n0.917,0.911,0.532,1\n0.276,0.757,0.927,2\n0.274,0.055,0.664,6\n" + \
  "22,7,0,1\n51,48,38,1\n69,40,16,0\n1,28,98,1"

LINES_MERGE = "x1,x2,x3,y\n2,29,30,1\n5,50,46,0\n1,7,89,1\n0,10,92,9\n4,11,8,1\n3,92,1,0"

LINES_TEXT = "x1,x2,x3,x4,y\n2000,Mercury,0.146851813,4,in\n3400,Mars,0.8655614457,1,in\n" + \
  "120,Venus,0.1147525953,2,out\n800,Earth,0.2786844389,6,in\n2100,Jupiter,0.8940182284,1,N/A\n" + \
  "2200,,0.7818682764,1,in\n200,Mars,0.4230423784,0,N/A\n18000,Jupiter,0.8164396221,1,out"

DIR = os.path.dirname(os.path.realpath(__file__))
FILENAME = os.path.join(DIR, 'tmp.csv')
FILENAME_MERGE = os.path.join(DIR, 'tmpi.csv')
FILENAME_TEXT = os.path.join(DIR, 'tmpt.csv')

FILENAME_DATASET = os.path.join(DIR, 'tmp.hdf5')

dataset_params = {
    'source_data_type': 'GENERAL',
    'target': FILENAME_DATASET,
    'version': 2,
    'iscreated': False,
    'num_columns': 4,
    'with_header': True,
    'delimiter': '\s*,\s*',
    'dtypes': ['f', 'f', 'f', 'i'],
    'classes': [[], [], [], []],
    'mean': [18.1095, 15.6899, 19.3516, 2],
    'stdev': [27.3196, 19.8914, 34.4553, 2],
	'min': [0.274, 0.055, 0, 0],
	'max': [69, 48, 98, 6],
    'output_class_counts': {'0': 1, '1': 4, '2': 1, '4': 1, '6': 1},
    'filters': [{'name': 'outputs', 'columns': []}]
}
dataset_merge_params = dataset_params.copy()
dataset_merge_params.update({
	'dtypes': ['i', 'i', 'i', 'i'],
	'mean': [2.5, 33.1667, 44.3333, 2],
	'stdev': [1.87083, 33.0903, 39.1748, 3.4641],
	'min': [0, 7, 1, 0],
	'max': [5, 92, 92, 9],
    'output_class_counts': {'0': 2, '1': 3, '9': 1},
})
dataset_text_params = {
    'data_type': 'GENERAL',
    'target': FILENAME_DATASET,
    'iscreated': False,
    'num_columns': 5,
    'version': 2,
    'delimeter': '\s*,\s*',
    'with_header': True,
    'dtypes': ['i', 'S', 'f', 'i', 'S'],
    'classes': [[], ['Earth', 'Jupiter', 'Mars', 'Mercury', 'Venus'], [], [], ['N/A', 'in', 'out']],
    'mean': [3602.5, None, 0.540152, 2, None],
    'stdev': [5924.29, None, 0.334579, 2, None],
    'min': [120, None, 0.114753, 0, None],
    'max': [18000, None, 0.894018, 6, None],
    'output_class_counts': {'N/A': 2, 'in': 4, 'out': 2},
	}


def create_tmp_file(content, filename):
    with open(filename, 'w') as f:
        f.write(content)
        f.close()


def wipe_tmp_file(filename):
    os.remove(filename)


@pytest.yield_fixture
@pytest.fixture
def filename():
    create_tmp_file(LINES, FILENAME)
    yield FILENAME
    wipe_tmp_file(FILENAME)


@pytest.yield_fixture
@pytest.fixture
def filename_merge():
    create_tmp_file(LINES_MERGE, FILENAME_MERGE)
    yield FILENAME_MERGE
    wipe_tmp_file(FILENAME_MERGE)


@pytest.yield_fixture
@pytest.fixture
def filename_text():
    create_tmp_file(LINES_TEXT, FILENAME_TEXT)
    yield FILENAME_TEXT
    wipe_tmp_file(FILENAME_TEXT)



def test_csv_load_from_lines():
    dataset = data_csv.GeneralDataset()
    dataset.load_from_lines(LINES)
    assert dataset.data.shape == (8, 4)


def test_csv_load_from_source(filename):
    dataset = data_csv.GeneralDataset()
    dataset_file = dataset.load_from_source(filename, **dataset_params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (8, 4)


def test_csv_load_from_lines_invalid():
    lines = "x1,x2,x3,y\n30,37,67,50\n93,error,55,24\n90,68,72,59\n23,35,76,8"
    kwargs = {'num_columns': 4, 'dtypes': ['i', 'i', 'i', 'i']}
    dataset = data_csv.GeneralDataset()
    dataset.load_from_lines(lines, **kwargs)
    assert dataset.data.shape == (3, 4)


def test_csv_load_from_lines_text_text_data():
    lines = "key,0.6398986743,60,C\nvalue,0.3999189187,6,A\niter,M,74,B\nnames,0.3242075364,15,A\n"+ \
      "any,0.9294471992,28,C\nother,0.503215279,90,A\nvalue,0.6827588778,96,A\nkeyword,0.5677838973,28,C\n" + \
      "new,0.131201321,53,B\nnames,0.5928324999,10,B\noverwrite,0.7019303145,38,C\n" + \
      "field,0.7117090842,71,C\ndefined,0.6661604231,60,A"
    kwargs = {
        'num_columns': 4,
        'dtypes': ['S', 'f', 'i', 'S'],
        'classes': [
            ['any', 'defined', 'field', 'iter', 'key', 'keyword', 'names', 'new', 'other', 'overwrite', 'value'],
            [], [], ['A', 'B', 'C']
        ]
    }
    dataset = data_csv.GeneralDataset()
    dataset.load_from_lines(lines, with_output=False, **kwargs)
    result = np.array([
        [ 4, 0.63989867, 60, 2],
        [10, 0.39991892,  6, 0],
        [ 6, 0.32420754, 15, 0],
        [ 0, 0.9294472,  28, 2],
        [ 8, 0.50321528, 90, 0],
        [10, 0.68275888, 96, 0],
        [ 5, 0.5677839,  28, 2],
        [ 7, 0.13120132, 53, 1],
        [ 6, 0.5928325,  10, 1],
        [ 9, 0.70193031, 38, 2],
        [ 2, 0.71170908, 71, 2],
        [ 1, 0.66616042, 60, 0]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_text_data(filename_text):
    dataset = data_csv.GeneralDataset()
    params = dataset_text_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': [4]},
    ]
    dataset_file = dataset.load_from_source(filename_text, **params)
    dataset.load(dataset_file=dataset_file)
    # NB: LINES_TEXT[5, 1] is missing. As all text data columns are permuted,
    # it is substituted with all zeros in order not to affect training.
    result = np.array([
        [  2.00000000e+03,  0.,  0.,  0.,  1.,  0.,  1.46851808e-01,  4.],
        [  3.40000000e+03,  0.,  0.,  1.,  0.,  0.,  8.65561426e-01,  1.],
        [  1.20000000e+02,  0.,  0.,  0.,  0.,  1.,  1.14752598e-01,  2.],
        [  8.00000000e+02,  1.,  0.,  0.,  0.,  0.,  2.78684437e-01,  6.],
        [  2.10000000e+03,  0.,  1.,  0.,  0.,  0.,  8.94018233e-01,  1.],
        [  2.20000000e+03,  0.,  0.,  0.,  0.,  0.,  7.81868279e-01,  1.],
        [  2.00000000e+02,  0.,  0.,  1.,  0.,  0.,  4.23042387e-01,  0.],
        [  1.80000000e+04,  0.,  1.,  0.,  0.,  0.,  8.16439629e-01,  1.]
    ])
    assert np.allclose(dataset.data, result)



def test_csv_load_from_source_shuffle(filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'shuffle'},
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [  2.20000000e+01,  7.00000000e+00,  0.00000000e+00,  1.00000000e+00],
        [  2.73999989e-01,  5.49999997e-02,  6.63999975e-01,  6.00000000e+00],
        [  1.00000000e+00,  2.80000000e+01,  9.80000000e+01,  1.00000000e+00],
        [  6.90000000e+01,  4.00000000e+01,  1.60000000e+01,  0.00000000e+00],
        [  4.09000009e-01,  7.96000004e-01,  6.89999998e-01,  4.00000000e+00],
        [  5.10000000e+01,  4.80000000e+01,  3.80000000e+01,  1.00000000e+00],
        [  2.75999993e-01,  7.57000029e-01,  9.26999986e-01,  2.00000000e+00],
        [  9.16999996e-01,  9.11000013e-01,  5.32000005e-01,  1.00000000e+00]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_normalize(filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'normalize'},
        ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [  1.96432206e-03,  1.54552087e-02,  7.04081636e-03,  6.66666687e-01],
        [  9.35599301e-03,  1.78537909e-02,  5.42857125e-03,  1.66666672e-01],
        [  2.91010674e-05,  1.46417767e-02,  9.45918355e-03,  3.33333343e-01],
        [  0.00000000e+00,  0.00000000e+00,  6.77551003e-03,  1.00000000e+00],
        [  3.16124916e-01,  1.44853473e-01,  0.00000000e+00,  1.66666672e-01],
        [  7.38090396e-01,  1.00000000e+00,  3.87755096e-01,  1.66666672e-01],
        [  1.00000000e+00,  8.33142161e-01,  1.63265303e-01,  0.00000000e+00],
        [  1.05636874e-02,  5.82855344e-01,  1.00000000e+00,  1.66666672e-01]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_shuffle_normalize(filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'shuffle'},
        {'name': 'normalize'}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [  3.16124916e-01,  1.44853473e-01,  0.00000000e+00,  1.66666672e-01],
        [  0.00000000e+00,  0.00000000e+00,  6.77551003e-03,  1.00000000e+00],
        [  1.05636874e-02,  5.82855344e-01,  1.00000000e+00,  1.66666672e-01],
        [  1.00000000e+00,  8.33142161e-01,  1.63265303e-01,  0.00000000e+00],
        [  1.96432206e-03,  1.54552087e-02,  7.04081636e-03,  6.66666687e-01],
        [  7.38090396e-01,  1.00000000e+00,  3.87755096e-01,  1.66666672e-01],
        [  2.91010674e-05,  1.46417767e-02,  9.45918355e-03,  3.33333343e-01],
        [  9.35599301e-03,  1.78537909e-02,  5.42857125e-03,  1.66666672e-01]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_split(monkeypatch, filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'split', 'start': 0, 'end': 80}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (6, 4)
    assert dataset.output is None

    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'split', 'start': 80, 'end': 100}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (2, 4)


def test_csv_load_from_source_permute(monkeypatch, filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'permute', 'columns': ['3']},
        ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [4.09000000e-01, 7.96000000e-01, 6.90000000e-01, 0., 0., 0., 1., 0., 0.],
        [9.17000000e-01, 9.11000000e-01, 5.32000000e-01, 1., 0., 0., 0., 0., 0.],
        [2.76000000e-01, 7.57000000e-01, 9.27000000e-01, 0., 1., 0., 0., 0., 0.],
        [2.74000000e-01, 5.50000000e-02, 6.64000000e-01, 0., 0., 0., 0., 0., 1.],
        [2.20000000e+01, 7.00000000e+00, 0.00000000e+00, 1., 0., 0., 0., 0., 0.],
        [5.10000000e+01, 4.80000000e+01, 3.80000000e+01, 1., 0., 0., 0., 0., 0.],
        [6.90000000e+01, 4.00000000e+01, 1.60000000e+01, 0., 0., 0., 0., 0., 0.],
        [1.00000000e+00, 2.80000000e+01, 9.80000000e+01, 1., 0., 0., 0., 0., 0.]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_permute_split(monkeypatch, filename, filename_merge):
    def mock_S3Key_get(key):
        return filename_merge

    dataset = data_csv.GeneralDataset()

    params = dataset_params.copy()    
    params['filters'] = [ {'name': 'permute', 'columns': [3]},
                          {'name': 'split',   'start': 0, 'end': 80} ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (6, 9)
    assert dataset.output is None

    params = dataset_merge_params.copy()
    params['filters'] = [ {'name': 'permute', 'columns': [0]},
                          {'name': 'split',   'start': 60, 'end': 100} ]
    dataset_file = dataset.load_from_source(filename_merge, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (3, 8)
    assert dataset.output is None

    params = dataset_merge_params.copy()
    params['filters'] = [ {'name': 'outputs', 'columns': [2, 3]},
                          {'name': 'permute', 'columns': [0]},
                          {'name': 'split',   'start': 0, 'end': 70} ]
    dataset_file = dataset.load_from_source(filename_merge, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (4, 6)
    assert dataset.output.shape == (4, 2)


def test_csv_load_from_source_ignore(filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [ {'name': 'outputs', 'columns': []},
                          {'name': 'ignore', 'columns': [1, 2]} ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [ 0.409, 4. ],
        [ 0.917, 1. ],
        [ 0.276, 2. ],
        [ 0.274, 6. ],
        [ 22.  , 1. ],
        [ 51.  , 1. ],
        [ 69.  , 0. ],
        [ 1.   , 1. ]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_ignore_permute(filename):
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [{'name': 'ignore',  'columns': [1, 2]},
                         {'name': 'permute', 'columns': [3]}]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    result = np.array([
        [ 0.40900001, 0., 0., 0., 1., 0., 0. ],
        [ 0.917,      1., 0., 0., 0., 0., 0. ],
        [ 0.27599999, 0., 1., 0., 0., 0., 0. ],
        [ 0.27399999, 0., 0., 0., 0., 0., 1. ],
        [ 22.,        1., 0., 0., 0., 0., 0. ],
        [ 51.,        1., 0., 0., 0., 0., 0. ],
        [ 69.,        0., 0., 0., 0., 0., 0. ],
        [  1.,        1., 0., 0., 0., 0., 0. ]
    ])
    assert np.allclose(dataset.data, result)


def test_csv_load_from_source_balance(monkeypatch, filename, filename_merge):
    dataset = data_csv.GeneralDataset()

    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'balance', 'sample': 'undersampling'}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (8, 4)

    # FAILS!
    # The output is of the shape (6, 3), while it has to be (3, 3)
    # There are 3 classes in the output: 0, 1, 9. 'Undersampling' strategy
    # implies reducing dataset to the size, where all classes presented by the
    # same number of examples as the class with the minimum number. In this case
    # it is class 9, that presented by only 1 example, thus there should be 3 lines
    # in the result dataset.
    #
    params = dataset_merge_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': ['3']},
        {'name': 'balance', 'sample': 'undersampling'}
    ]
    dataset_file = dataset.load_from_source(filename_merge, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (3, 3)
    assert np.all(np.sort(dataset.output.T[0]) == np.array([0, 1, 9]))

    # FAILS
    # The result for oversampling strategy with no split filter should consist of
    # all the examples from the original dataset plus additional examples, randomly
    # picked from the original dataset so that the number of examples of each class
    # becomes equal with the maximum number of examples of a certain class. In the
    # example of filename_merge this class is 1, but the output consists of the
    # examples of ONLY class 1:
    #
    # [  2.  29.  30.] [ 1 ]
    # [  1.   7.  89.] [ 1 ]
    # [  1.   7.  89.] [ 1 ]
    # [  4.  11.   8.] [ 1 ]
    # [  4.  11.   8.] [ 1 ]
    #
    # However it should look like this (doesn't have to be ordered the same way):
    #
    # [  2.  29.  30.] [ 1 ]
    # [  1.   7.  89.] [ 1 ]
    # [  4.  11.   8.] [ 1 ]
    # [  3.  92.   1.] [ 0 ]
    # [  5.  50.  46.] [ 0 ]
    # [  3.  92.   1.] [ 0 ]
    # [  0.  10.  92.] [ 9 ]
    # [  0.  10.  92.] [ 9 ]
    # [  0.  10.  92.] [ 9 ]
    #
    params = dataset_merge_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': ['3']},
        {'name': 'balance', 'sample': 'oversampling'}
    ]
    dataset_file = dataset.load_from_source(filename_merge, **params)
    dataset.load(dataset_file=dataset_file)
    output = np.array([0, 0, 0, 1, 1, 1, 9, 9, 9])
    assert dataset.data.shape == (9, 3)
    assert np.all(np.sort(dataset.output.T[0]) == output)

    # FAILS
    # The output is of the shape (5, 3), while it has to be (9, 3)
    # The same as above - it consists only of the examples of the most populated class 1
    # In case of 'uniform' balancing it is impossible to predict what exactly examples
    # will be chosen for the result dataset, but nevertheless all classes should be presented.
    #
    params = dataset_merge_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': ['3']},
        {'name': 'balance', 'sample': 'uniform'}
    ]
    dataset_file = dataset.load_from_source(filename_merge, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (9, 3)


# FAILS!
# Merge not yet done.
def test_csv_load_from_source_merge(monkeypatch, filename, filename_merge):
    def mock_S3Key_get(key):
        return filename_merge

    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': []},
        {'name': 'merge', 'datas': [filename_merge]}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    dataset.load(dataset_file=dataset_file)
    assert dataset.data.shape == (14, 4)


# FAILS!
# Merge not yet done.
def test_csv_load_from_source_merge_with_output(monkeypatch, filename, filename_merge):
    def mock_S3Key_get(key):
        return filename_merge

    monkeypatch.setattr(S3Key, 'get', mock_S3Key_get)
    dataset = data_csv.GeneralDataset()
    params = dataset_params.copy()
    params['filters'] = [
        {'name': 'outputs', 'columns': ['2', '3']},
        {'name': 'merge', 'datas': [filename_merge]}
    ]
    dataset_file = dataset.load_from_source(filename, **params)
    assert dataset.data.shape == (14, 2)
    assert dataset.output.shape == (14, 2)
