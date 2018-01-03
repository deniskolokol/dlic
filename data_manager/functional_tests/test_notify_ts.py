import mock
import pytest
from dmworker.parser import parse, global_notify
from dmworker.exception import InvalidTimeseries
from dmworker.fileutils import TempFile


def pass_template(data,log,exp_meta):
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.ts') as ts:
        with global_notify(notify):
            meta = parse(ts)
    for key in exp_meta:
        assert meta[key] == exp_meta[key]
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def fail_template(data,log):
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.ts') as ts:
        with global_notify(notify):
            with pytest.raises(InvalidTimeseries):
                parse(ts)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_ts_valid_homogeneous():
    data = '1.0,.2,0.3|0,1;2e-27,3e+10,0.000000004|1,0\n1,2.,3|0,1;2,3,4|1,0;'
    log = "First timestep has 3 inputs and 2 outputs. Applying this requirement to the entire file."
    exp_meta = {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 2,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'binary_input': False,
        'binary_output': True,
    }
    pass_template(data,log,exp_meta)


def test_parse_ts_valid_heterogeneous():
    data = '0,1|1,2,3;1,0|2,3,4\n0,1|3,4,5;'
    log = 'First timestep has 2 inputs and 3 outputs. Applying this requirement to the entire file.'
    exp_meta = {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 0,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 2,
        'output_size': 3,
        'binary_input': True,
        'binary_output': False,
    }
    pass_template(data,log,exp_meta)

def test_parse_ts_valid_emptyrow():
    data = '1,2,3|0,1;2,3,4|1,0\n\n1,2,3|0,5'
    log = 'First timestep has 3 inputs and 2 outputs. Applying this requirement to the entire file.'
    exp_meta = {
        'data_type': 'TIMESERIES',
        'data_rows': 2,
        'empty_rows': 1,
        'min_timesteps': 1,
        'max_timesteps': 2,
        'input_size': 3,
        'output_size': 2,
        'binary_input': False,
        'binary_output': False,
    }
    pass_template(data,log,exp_meta)


def test_parse_ts_invalid():
    data = '0,1|0,1\n0,1|0,1|0,1'
    log = """
    First timestep has 2 inputs and 2 outputs. Applying this requirement to the entire file.
    Not allowed character or improperly formatted timeseries on line 2.
    """
    fail_template(data,log)


def test_parse_ts_irregular_io_count():
    data = '0,1|2;1,0|3;1,1|4,5'
    log = """
    First timestep has 2 inputs and 1 outputs. Applying this requirement to the entire file.
    Oops! Timestep 3 on line 1 has 2 inputs and 2 outputs.
    """
    fail_template(data,log)


def test_parse_ts_nonfloat_value():
    """Test ValueError condition in parser.py line 250. Said condition is
    presently dominated by regex validity test in function parse_ts. Regex
    test should be weakened to isolate misformatting and non-float as
    separate failure states.
    """
    data = '0,1,2|0,1;1,0,2|0,1\n1,0,2|0,1a;1,2,3|1,0'
    log = """
    First timestep has 3 inputs and 2 outputs. Applying this requirement to the entire file.
    Not allowed character or improperly formatted timeseries on line 2.
    """
    fail_template(data, log)


def test_parse_ts_null_input():
    data = ''
    log = 'File contains no data.'
    fail_template(data,log)
