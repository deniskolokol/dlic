from collections import Counter
import mock
import pytest
from dmworker.exception import InvalidTimeseries
from dmworker.parser import parse_timestep, parse_ts, set_notify


set_notify(mock.MagicMock())


def test_timestep_valid():
    classes = Counter()
    inv = '1, 0, 1, 0, 1'.split(',')
    outv = '0., 0., 1.'. split(',')
    bin = bout = True
    classes, bin, bout = parse_timestep(inv, outv, classes, bin, bout)
    assert bin
    assert bout
    assert dict(classes) == {'2': 1}

    inv = '1, 2, 3,4,5'.split(',')
    outv = '0, 0, 1'. split(',')
    classes, bin, bout = parse_timestep(inv, outv, classes, bin, bout)
    assert not bin
    assert bout
    assert dict(classes) == {'2': 2}

    classes = Counter()
    inv = '1, 0, 1, 0, 1'.split(',')
    outv = '0, 1, 0.5'. split(',')
    classes, bin, bout = parse_timestep(inv, outv, classes, bin, bout)
    assert not bin
    assert not bout
    assert dict(classes) == {}

    inv = '1, 0, 1, 0, 1'.split(',')
    outv = '0., 0., 1.'. split(',')
    classes, bin, bout = parse_timestep(inv, outv, classes, bin, bout)
    assert not bin
    assert not bout
    assert dict(classes) == {}


def test_ts_valid():
    data = iter(['1,2,3.|0., 1.;2,3,3|1,0;0,9.1,0|0,1',
                 '2,2.,2|1,0;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 3,
        'input_size': 3,
        'output_size': 2,
        'classes': {'0': 2, '1': 2},
        'binary_input': False,
        'binary_output': True,
    }

    data = iter(['2,2.,2|1,0;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 1,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 1,
        'input_size': 3,
        'output_size': 2,
        'classes': {'0': 1},
        'binary_input': False,
        'binary_output': True,
    }

    data = iter(['1, 0, 0|0, 1; 1.0, 0.0, 0.0| 0, 1',
                 '0, 0, 1|1, 0;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'classes': {'0': 1, '1': 2},
        'binary_input': True,
        'binary_output': True,
    }

    data = iter(['1, 0, 0|0, 1; 1.0, 0.0, 0.0| 0, 1',
                 '0, 0, 1|1, -0.11233;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'classes': {},
        'binary_input': True,
        'binary_output': False,
    }

    data = iter(['', '1, 0, 0|0, 1; 1.0, 0.0, 0.0| 0, 1', '',
                 '0, 0, 1|1, -0.11233;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 2,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'classes': {},
        'binary_input': True,
        'binary_output': False,
    }

    data = iter(['', '1, 0, 0|0, 1; 1.0, 0.0, 0.0| 0, 1', '',
                 '0, 0, 1|1, 1;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 2,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'classes': {},
        'binary_input': True,
        'binary_output': False,
    }


def test_ts_valid_only_input():
    data = iter(['', '1, 0, 0.0; 1.0, 0.0, 0.0', '',
                 '0, 0, 1;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 2,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 0,
        'classes': {},
        'binary_input': True,
        'binary_output': False,
    }

    data = iter(['1.3; 2.1', '0;'])
    meta = parse_ts(data)
    assert meta == {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 1,
        'output_size': 0,
        'classes': {},
        'binary_input': False,
        'binary_output': False,
    }


def test_ts_invalid_only_input():
    data = iter(['', '1, 0, 0; 1.0, 0.0, 0.0', '',
                 '0, 0, 1|1, 0; 0, 0, 1|1, 2;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Oops! Timestep 1 on line 4 has 3 inputs and 2 outputs.'

    data = iter(['1, 0, 0; 1.0, 0.0, 0.0|1, 0; 1,1,1;', '',
                 '0, 0, 1; 0, 0, 1;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Not allowed character or improperly formatted timeseries on line 1.'

    data = iter(['1, 0, 0; 1.0, 0.0, 0.0; 1,1,1;', '',
                 '0, 0, 1;|0, 0, 1;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Not allowed character or improperly formatted timeseries on line 3.'


def test_ts_invalid():
    data = iter(['2,2.,2|1,0;;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Not allowed character or improperly formatted timeseries on line 1.'

    data = iter(['2,2,2|1,0;2,2|1,0;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Oops! Timestep 2 on line 1 has 2 inputs and 2 outputs.'

    data = iter(['2,2,2|1,0;', '2,2|1,0;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Oops! Timestep 1 on line 2 has 2 inputs and 2 outputs.'

    data = iter(['2,2,2|1,0;2,2,2|1;'])
    with pytest.raises(InvalidTimeseries) as excinfo:
        parse_ts(data)
    assert excinfo.value.message == 'Oops! Timestep 2 on line 1 has 3 inputs and 1 outputs.'
