import pytest
import mock
from dmworker.parser import parse_csv, set_notify, LastColumnCounter
from dmworker.exception import InvalidCSV


set_notify(mock.MagicMock())


def test_comma():
    data = iter(["1, 2, 3, 4", "  2, 3, 4, 5",
                 "3 ,4 , 5,  6", "4 ,   5, 1, 0   "])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}
    data = iter([" abc, b ,c test , d    ", "  2, 3, 4, 5",
                 "3 ,4 , 5,  6", "4 ,   5, 1, 0   "])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_whitespace():
    data = iter(["1  2  3  4", "  2  3  4  5",
                 "3  4   5   6", "4     5  1  0   "])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\\s+',
                    'data_type': 'GENERAL',
                    'num_columns': 4}
    data = iter([" a  b  c   d    ", "  2  3  4  5",
                 "3  4   5   6",  "4     5  1  0   "])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\\s+',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_tab():
    data = iter(["1\t2\t3\t4", "2\t3\t4\t5",
                 "3\t4\t5\t6", "4\t5\t1\t0\t"])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s+',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_empty_rows():
    data = iter(['', '1,2,3,4', '5,6,7,8'])
    with pytest.raises(InvalidCSV) as excinfo:
        parse_csv(data)
    assert excinfo.value.message == 'First row is empty, it must contain headers or data.'
    data = iter([])
    with pytest.raises(InvalidCSV) as excinfo:
        parse_csv(data)
    assert excinfo.value.message == 'First row is empty, it must contain headers or data.'
    data = iter(['1,2,3,4', '', '5,6,7,8'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}
    data = iter(['asd, bcx, asd'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\\s*,\\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 3}


def test_invalid_values():
    data = iter(['1, 2, test, 4', '2,3,4,5', '1,2,3,4'])
    assert parse_csv(data)

    data = iter(['1, 2, test, 4', '2,3,val,5', '1,2,3,4'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}
    data = iter(['1', '2', '1'])
    with pytest.raises(InvalidCSV) as excinfo:
        parse_csv(data)
    assert excinfo.value.message == 'CSV doesn\'t contain a valid delimiter.'

    data = iter(['1,2,3,0', '1,2,3,0', '3,4,1,1', '1,1,1,1', '0,0,0,'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_floats():
    data = iter(['1 2 3.4 1', '1. .23 0.1 0.00001', '12e-6 32e+6 0.0 33'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s+',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_classes():
    data = iter(['1,2,3,0', '1,2,3,0', '3,4,1,1', '1,1,1,1', '0,0,0,0', '2,2,2,2'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 4}


def test_no_output():
    data = iter(['1,2,3,0,1.1', '1,2,3,0,1.3', '3,4,1,1,0.5',
                 '1,1,1,1,0', '0,0,0,0,1', '2,2,2,2,0.8'])
    meta = parse_csv(data)
    assert meta == {'delimeter': '\s*,\s*',
                    'data_type': 'GENERAL',
                    'num_columns': 5}


def test_last_column_counter():
    data = [1.0, 2., 3, 4, 0, 1.0, 0, 1, 2, 5]
    counter = LastColumnCounter()
    for x in data:
        counter.update(x)
    assert counter.get_result() == {
        'classes': {'0': 2, '1': 3, '2': 2, '3': 1, '4': 1, '5': 1},
        'max': 5.0,
        'min': 0.0,
        'unique': 6
    }


def test_last_column_counter_over_1000():
    data = range(1100) * 2
    counter = LastColumnCounter()
    for x in data:
        counter.update(x)
    assert counter.get_result() == {
        'classes': None,
        'max': 1099.,
        'min': 0.0,
        'unique': None,
    }


def test_last_column_counter_over_200():
    data = range(210) * 2
    counter = LastColumnCounter()
    for x in data:
        counter.update(x)
    assert counter.get_result() == {
        'classes': None,
        'max': 209.,
        'min': 0.0,
        'unique': 210,
    }
