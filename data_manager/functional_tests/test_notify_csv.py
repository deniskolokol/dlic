import mock
import pytest
from dmworker.parser import parse, global_notify
from dmworker.exception import InvalidCSV
from dmworker.fileutils import TempFile


def test_parse_with_csv():
    data = 'a,b,c,d\n\n1,2,3,4\n5,6,7,8\n'
    log = """
    Parsing CSV with comma as delimiter.
    Found 4 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset appears to have a header.
    Found 2 samples.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            meta = parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert meta['data_type'] == 'GENERAL'
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_with_invalid_csv():
    # Since we accept text columns, we presume that strings appear to be errors
    # only if it's less than 10% of them in a column. Hence it can be tested
    # only on a dataset with minimum 11 columns, where one contains string.
    #
    data = '1 2 3 4\n1 2 3 4\n5 6 a 8\n7 6 5 2\n8 8 8 8\n2 2 3 9\n5 6 7 8\n12 13 45 56\n12 43 6 7\n9 9 9 0\n1 2 5 0\n'
    log = """
    Parsing CSV with whitespace (tab) as delimiter.
    Found 4 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    No header found, first row contains data.
    Found 1 row with invalid values:
    - row 3, column 3
    Found 10 samples.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_with_invalid_csv_with_null_bytes():
    data = "1 2 3 4\n1 2 3 4\n5 6 \\x00 8\n7 6 5 2\n8 8 8 8\n2 2 3 9\n5 6 7 8\n12 13 45 56\n12 43 6 7\n9 9 9 0\n1 2 5 0\n"
    log = """
    Parsing CSV with whitespace (tab) as delimiter.
    Found 4 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    No header found, first row contains data.
    Found 1 row with invalid values:
    - row 3, column 3
    Found 10 samples.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_with_invalid_csv_other_file_type():
    data = '%PDF-1.4\n'
    log = """
    CSV doesn't contain a valid delimiter.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_with_invalid_csv_other_file_type_valid_delimiter():
    data = '%PDF,-1.4\nadsadsadsad'
    log = """
    Parsing CSV with comma as delimiter.
    Found 2 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset is empty or isn't properly formatted.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))


def test_parse_invalid_delimiter():
    data = '3:4:5:4:dsf:/n'
    log = """
    CSV doesn't contain a valid delimiter.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_invalid_first_line():
    data = '123,'
    log = """
    Parsing CSV with comma as delimiter.
    With selected delimiter found only 1 columns in first row, must be at least 2.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_rows_non_consistent():
    # Warning! No error here: inconsisten rows ignored by np.genfromtxt
    data = '1,2,3,4,5,6,7,8\n8,7,6,5,4,3,2,1\n56,34,34\n'
    log = """
    Parsing CSV with comma as delimiter.
    Found 8 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    No header found, first row contains data.
    Found 1 row with invalid values:
    - row 3, column 4
    Found 2 samples.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            meta = parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert meta['data_type'] == 'GENERAL'
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_only_two_row():
    data = ' \n4,\n'
    log = """
    First row is empty, it must contain headers or data.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_different_delimiters_per_Row():
    data = '4 5\n4,6\n'
    log = """
    Parsing CSV with whitespace (tab) as delimiter.
    Found 2 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset is empty or isn't properly formatted.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_no_data():
    data = ''
    log = """
    First row is empty, it must contain headers or data.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_not_enough_columns():
    data = '3,\n 4,,5\n6,8,9\n'
    log = """
    Parsing CSV with comma as delimiter.
    With selected delimiter found only 1 columns in first row, must be at least 2.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_bad_column_data_first_row_empty():
    data = '3,,,\n4,\n6,8,9\n'
    log = """
    Parsing CSV with comma as delimiter.
    Found 4 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset is empty or isn't properly formatted.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_bad_column_data_first_row():
    data = '3,\\x00,4,3\n4,\n6,8,9\n'
    log = """
    Parsing CSV with comma as delimiter.
    Found 4 fields in first row, assume all the rows have this number of fields.
    Parsing...
    Analyzing data...
    The dataset is empty or isn't properly formatted.
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called


def test_parse_invalid_delimiter2():
    data = '3:4:5:4:dsf:/n/n/n/n/n/n/n/n/n/n/n/n/n/n/n/n/n'
    log = """
    CSV doesn't contain a valid delimiter.
    This means your file isn't properly formatted
    (or you submitted another type of file).
    """
    notify = mock.MagicMock()
    notify.send = mock.MagicMock()
    notify.admin_send = mock.MagicMock()
    with TempFile(data, suffix='.csv') as csv:
        with global_notify(notify):
            with pytest.raises(InvalidCSV):
                parse(csv)
    rval = '\n'.join(x[0][0] for x in notify.send.call_args_list)
    assert rval == '\n'.join(x.strip() for x in log.strip().split('\n'))
    assert not notify.admin_send.called
