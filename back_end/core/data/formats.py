import re
import numpy as np
from .. import get_logger
from .utils import open_datafile
from ..exception import DataFileError
from ..aws import S3Key


log = get_logger('erstaz.data.formats')
STR_TYPES = ('S', 'a', 'b', 'U',)
FORMAT_ERROR_MSG = '''
                   Data file has invalid format.
                   File should contain data columns delimited with a space or a comma.
                   A header row is allowed.
                   '''
INVALID_ERROR_MSG = '''
                    Invalid data file.
                    File contains wrong number of columns or has invalid format.
                    '''

class CsvDataFile(object):

    def __init__(self, dataset, **kwargs):
        self.skip_header = int(kwargs.get('with_header', False))
        self.classes = kwargs.get('classes', [])
        self.dtypes = kwargs.get('dtypes', [])
        self.num_columns = kwargs.get('num_columns', 0)
        self.error_lines = []
        self.delimiter = kwargs.get('delimiter', None)
        if self.delimiter == r'\s*,\s*':
            self.delimiter = ',' 
        elif self.delimiter == r'\s+':
            self.delimiter = ' '
        self.dataset = dataset
        if isinstance(dataset, S3Key):
            self.data = dataset.get()
        else:
            if isinstance(dataset, (str, unicode)):
                if self.delimiter:
                    self.data = open_datafile(dataset)
                else:
                    datafile = open_datafile(dataset)
                    self.data = self._skip_header_parse_delimiter(datafile)
            else:
                self.data = self._skip_header_parse_delimiter(dataset)

    def load_to_ndarray(self, shuffle=True, rng=None):
        try:
            data = self._do_load_to_ndarray()
            if len(data.shape) == 1:
                data = data.reshape((-1, data.shape[0]))
        except ValueError as e:
            log.critical('numpy loadtxt raised: %s' % e.message)
            if e.message == 'setting an array element with a sequence.':
                raise DataFileError('Data file has invalid format.\n'
                    'Most probably file contains rows with different length.',
                    show_to_user=True)
            raise DataFileError(
                'The datafile has an invalid format, there\'s an error in line %s' % self.current_line,
                show_to_user=True)
        if shuffle:
            rng = rng if rng is not None else np.random.RandomState(123)
            rng.shuffle(data)
        return data

    def _do_load_to_ndarray(self):
        data = np.genfromtxt(self.data, delimiter=self.delimiter,
                             skip_header=self.skip_header,
                             invalid_raise=False, dtype=None)
        if not self.skip_header:
            data = self._double_check_header(data)
        try:
            data.shape[1]
            data = data.astype(float)
        except (IndexError, ValueError):
            if data.shape == ():
                data = self._one_line(data)
            else:
                data = self._walk_columns(data)
        mask = np.isnan(data).any(1)
        self.error_lines = np.sort(np.where(mask)[0]).tolist()
        return data[~mask]

    def _one_line(self, in_):
        out_ = np.empty(self.num_columns)
        for i, val in enumerate(in_.tolist()):
            try:
                dtype = self.dtypes[i]
            except IndexError:
                dtype = None
            if dtype in STR_TYPES:
                try:
                    out_[i] = self.classes[i].index(val)
                except ValueError:
                    out_[i] = np.nan
            elif dtype == '-':
                out_[i] = 0
            else:
                out_[i] = val
        return np.array([out_])

    def _walk_columns(self, in_):
        try:
            self.num_columns = in_.shape[1]
        except IndexError:
            if in_.dtype.kind == 'V':
                in_ = in_.reshape((in_.size,))
            else:
                in_ = in_.reshape((1, in_.size))
            self.num_columns = len(in_[0])
        out_ = np.empty((len(in_), self.num_columns))
        for col in range(self.num_columns):
            try:
                values = in_['f%d' % col]
            except ValueError:
                try:
                    values = in_[:, col]
                except IndexError:
                    raise DataFileError(INVALID_ERROR_MSG, show_to_user=True)
            try:
                dtype = self.dtypes[col]
            except IndexError:
                dtype = None
            if dtype in STR_TYPES:
                classes = np.array(self.classes[col])
                index = np.searchsorted(classes, values)
                values_index = np.take(np.argsort(classes), index, mode='clip')
                mask = classes[values_index] != values
                masked = np.ma.array(values_index, mask=mask)
                column = masked.data.astype(float)
                column[mask] = np.nan
            elif dtype == '-':
                column = np.zeros(len(values))
            else:
                column = np.genfromtxt(values.astype('S'))
            out_[:, col] = column
        return out_

    def _double_check_header(self, in_):
        # self.skip_header arrives to __init__ from kwargs, which can
        # indicate header in a training set. Double-check for prediction.
        if len(in_.dtype) == 0 and in_.dtype.kind == 'S':
            if (in_[0] == in_).sum() == in_.shape[1]:
                return in_[1:]
        return in_

    def _skip_header_parse_delimiter(self, lines):
        self.current_line = 0

        # we will explicitly add delimiter to the end of the line,
        # because I don't know how to rewrite this without
        # catastrophic backtracking
        # http://www.regular-expressions.info/catastrophic.html
        # Also may be useful to add https://pypi.python.org/pypi/timeout
        # in case regexp still has backtracking
        re_template = r'^(([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)|[A-Za-z0-9_\.-]+)?(%s))+$'
        re_comma = re.compile(re_template % '\,\s*')
        re_space = re.compile(re_template % '\s+')

        def parse():
            for line in lines:
                self.current_line += 1
                if re_space.match(line.rstrip() + ' '): # hack for regexp
                    match = lambda x: re_space.match(x.rstrip() + ' ')
                    yield None
                    yield line
                    break
                if re_comma.match(line.rstrip('\r\n, ') + ','): # hack for regexp
                    match = lambda x: re_comma.match(x.rstrip('\r\n, ') + ',')
                    yield ',' # yield delimiter first
                    yield line
                    break
            for line in lines: # check for lines with wrong values
                if match(line):
                    self.current_line += 1
                    yield line
        parser = parse()
        try:
            self.delimiter = parser.next()
        except StopIteration:
            raise DataFileError(FORMAT_ERROR_MSG, show_to_user=True)
        return parser
