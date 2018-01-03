import os
import pytest
import cStringIO
import numpy as np
from ersatz.data import timeseries as ts
from ersatz.mrnn.util import calculate_batch_size


LINES = ("32,1,12,345|0,1;3,1,1,0|0,1;3,12,2,12|0,1\n"
         "-4,6,1,37|1,0;-2,1,-14,4|0,1;1,1,29,7|1,0\n"
         "-1,0,3,0|0,1;4,3,-2,0|0,1\n"
         "1,10,3,2|1,0;2,0,0,1|0,1;15,15,0,0|0,1\n"
         "2,2,-1,-50|0,1;2,1,-10,14|0,1;1,1,3,7|1,0\n"
         "-1,0,3,0|0,1;5,5,-5,0|0,1")
FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tmp.ts')


def io(data):
    return cStringIO.StringIO(data)


@pytest.yield_fixture
@pytest.fixture
def filename():
    with open(FILENAME, 'w') as f:
        f.write(LINES)
        f.close()
    yield FILENAME
    os.remove(FILENAME)


def test_timeseries_load_from_lines():
    timeseries = ts.Timeseries()
    timeseries.load_from_lines(io(LINES), quantiles=None)

    # after to_mrnn_shape
    data = timeseries.get_training_data()[0]
    assert data.shape == (3, 6, 6)
    assert timeseries.quantiles is None
    assert all(np.isnan(data[2][4]))


def test_timeseries_load_from_source(filename):
    timeseries = ts.Timeseries()
    timeseries.load_from_source(filename)
    assert timeseries.data.shape == (6, 3, 6)
    assert timeseries.in_mrnn_format == False
    assert timeseries.get_training_data()[0].shape == (3, 6, 6)
    assert timeseries.in_mrnn_format
    assert all(np.isnan(timeseries.data[2][4]))


def test_timeseries_binarize():
    data = io('1,1,1|1,0;1,1,1|0,1\n2,2,2|0,0;2,2,2|1,1\n3,3,3|0,0;')
    data, len_output, _ = ts.load_timeseries_from_lines(data, binarize=True)
    quantiles = ts.calculate_quantiles(data, len_output)
    data = ts.convert_to_2bit_binary(data, len_output, quantiles)
    assert data.shape == (3, 2, 8)
    assert quantiles == [(1.0, 2.0, 2.0), (1.0, 2.0, 2.0), (1.0, 2.0, 2.0)]
    result = np.array(
        [[[  0.,   0.,   0.,   0.,   0.,   0.,   1.,   0.],
          [  0.,   0.,   0.,   0.,   0.,   0.,   0.,   1.]],

         [[  0.,   1.,   0.,   1.,   0.,   1.,   0.,   0.],
          [  0.,   1.,   0.,   1.,   0.,   1.,   1.,   1.]],

         [[  1.,   1.,   1.,   1.,   1.,   1.,   0.,   0.],
          [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]]]
    )
    assert np.all(result[~np.isnan(result)] == data[~np.isnan(result)])


def test_timeseries_load_from_source_split(filename):
    timeseries = ts.Timeseries()
    timeseries.load_from_source(filename,
                                filters=[{'name': 'split',
                                          'start': 0, 'end': 80}])
    # 80% is 4
    assert timeseries.data.shape == (4, 3, 6)
    assert timeseries.in_mrnn_format == False
    assert timeseries.get_training_data()[0].shape == (3, 4, 6)
    assert timeseries.in_mrnn_format


def test_timeseries_load_from_source_multiple_filters(filename):
    timeseries = ts.Timeseries()
    filters = [{'name': 'binarize'},
               {'name': 'split', 'start': 80, 'end': 100}]
    timeseries.load_from_source(filename, filters=filters)
    assert timeseries.quantiles.shape == (4, 3)
    assert timeseries.data.shape == (2, 3, 10)
    assert timeseries.in_mrnn_format == False
    assert timeseries.get_training_data()[0].shape == (3, 2, 10)
    assert timeseries.in_mrnn_format


def test_min_batch_size():
    min_batches = 3
    dataset_size = 5
    max_batch_size = 10
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 1
    assert num_batches == 5

def test_batch_size_2():
    min_batches = 3
    dataset_size = 6
    max_batch_size = 10
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 2
    assert num_batches == 3


def test_max_batch_size():
    min_batches = 3
    dataset_size = 610
    max_batch_size = 100
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 100
    assert num_batches == 7

def test_max_batch_size_1():
    min_batches = 1
    dataset_size = 1000
    max_batch_size = 350
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 350
    assert num_batches == 3

def test_max_batch_size_3():
    min_batches = 3
    dataset_size = 1000
    max_batch_size = 350
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 350
    assert num_batches == 3

def test_max_batch_size_4():
    min_batches = 4
    dataset_size = 1000
    max_batch_size = 350
    batch_size, num_batches = calculate_batch_size(dataset_size,
                                                   max_batch_size,
                                                   min_batches)
    assert batch_size == 1000/4
    assert num_batches == 4
