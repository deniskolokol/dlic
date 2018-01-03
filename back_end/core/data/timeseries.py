import numpy as np
from . import utils
from .base import BaseDataset
from .formats import open_datafile
from ..aws import S3Key
from ..exception import DataFileError, ApiParamsError


def get_data(file_name):
    '''ersatz_predict.py uses this method'''
    key = S3Key(file_name)
    return key.get()


def extend_with_nans_new(batches):
    T = batches[0].shape[1]
    shape = batches[0].shape
    for i in range(1, len(batches)):
        shape = (batches[i].shape[0], T - batches[i].shape[1],
                 batches[i].shape[2])
        aa = np.tile(np.nan, shape)
        batches[i] = np.hstack((batches[i], aa))
    return np.vstack(batches)


def load_timeseries_from_s3(s3_filename, binarize=False):
    filename = get_data(s3_filename)
    return load_timeseries_from_file(filename, binarize)


def load_timeseries_from_file(filename, binarize=False):
    data = open_datafile(filename)
    return load_timeseries_from_lines(data, binarize)


def load_timeseries_from_lines(data, binarize=False):
    data = strip_split_samples(data)
    len_input, len_output, splitter = get_timestep_split(data[0][0])
    return load_timeseries(data, len_output, len_input, splitter, binarize)


def load_timeseries(data, len_output, len_input, splitter, binarize=False):
    data = construct_array(data, len_output, len_input, splitter, binarize)
    return data, len_output, np.arange(data.shape[0])


def strip_split_samples(data):
    return [line.strip().strip(';').split(';') for line in data
            if len(line.strip().strip(';')) > 0]


def get_timestep_split(timestep):
    """
    it gets timestep like "1,2,3|2,2" or for predict case "1,2,3"
    and returns len of input/output and lambda which can convert
    string timestep to list
    """
    timestep = timestep.strip().strip(';|,')
    timestep = [x.split(',') for x in timestep.split('|')]
    if len(timestep) == 1:
        len_input, len_output = len(timestep[0]), 0
        splitter = lambda x, _: [y.split(',') for y in x.split('|')] + [[]]
    else:
        len_input, len_output = [len(x) for x in timestep]
        splitter = lambda x, _: [y.split(',') for y in x.split('|')]
    return len_input, len_output, splitter


def sample_preprocess(sample, len_output, len_input, splitter, binarize):
    rval = []
    for timestep in sample:
        inputs, outputs = splitter(timestep, len_input)
        if len(inputs) != len_input:
            raise DataFileError("Inconsistent number of inputs")
        if len(outputs) != len_output:
            raise DataFileError("Inconsistent number of outputs")
        if binarize:
            inputs = [y for x in zip(inputs, [0] * len_input) for y in x]
        inputs.extend(outputs)
        rval.append(inputs)
    return rval


def construct_array(data, len_output, len_input, splitter, binarize):
    max_sample_size = max(len(x) for x in data)
    if binarize:
        timestep_size = 2 * len_input + len_output
    else:
        timestep_size = len_input + len_output
    rval = np.empty((len(data), max_sample_size, timestep_size), dtype=np.float32)
    for i, x in enumerate(data):
        x = sample_preprocess(x, len_output, len_input, splitter, binarize)
        x = np.array(x, dtype=np.float32)
        shape = (max_sample_size - len(x), timestep_size)
        if shape[0]:
            nans = np.tile(np.nan, shape)
            x = np.vstack((x, nans))
        rval[i] = x
    return rval


def calculate_quantiles(data, len_output):
    quantiles = []
    for column in range(0, data.shape[2] - len_output, 2):
        data_ = data[:, :, column]
        quarter1 = np.percentile(data_[~np.isnan(data_)], 25)
        quarter2 = np.percentile(data_[~np.isnan(data_)], 50)
        quarter3 = np.percentile(data_[~np.isnan(data_)], 75)
        quantiles.append((quarter1, quarter2, quarter3))
    return quantiles


def convert_to_2bit_binary(data, len_output, quantiles):
    iquantiles = iter(quantiles)
    for column in range(0, data.shape[2] - len_output, 2):
        try:
            quarter1, quarter2, quarter3 = iquantiles.next()
        except IndexError:
            raise ApiParamsError('Quantiles and shapes doesn\'t match. '
                                 'Try to restart this model.')
        for i in xrange(data.shape[0]):
            for j in xrange(data.shape[1]):
                value = data[i][j][column]
                if np.isnan(value):
                    data[i][j][column:column + 2] = [np.NaN, np.NaN]
                elif value <= quarter1:
                    data[i][j][column:column + 2] = [0, 0]
                elif value <= quarter2:
                    data[i][j][column:column + 2] = [0, 1]
                elif value <= quarter3:
                    data[i][j][column:column + 2] = [1, 0]
                else:
                    data[i][j][column:column + 2] = [1, 1]
    return data


def binarize(data, len_output, quantiles=None):
    if quantiles is None:
        quantiles = calculate_quantiles(data, len_output)
    data = convert_to_2bit_binary(data, len_output, quantiles)
    return data, np.array(quantiles)


def split(data, original_order, start, end):
    size = data.shape[0]
    start = int(size * (start / 100.0))
    end = int(size * (end / 100.0))
    data = data[start:end]
    original_order = original_order[start:end]
    return data, original_order


def shuffle(data, original_order):
    raise NotImplementedError()


def merge(data):
    raise NotImplementedError()


class Timeseries(BaseDataset):
    def __init__(self, **kwargs):
        self.quantiles = None
        self.original_order = None
        self.source_data_type = "TIMESERIES"
        self.in_mrnn_format = False
        super(Timeseries, self).__init__()

    def load_from_source(self, source_file, filters=None, **kwargs):
        data = self._load_source(source_file, filters)
        self.data = self._apply_filters_pipeline(data, filters)
        self.is_loaded = True

    def _load_source(self, source_file, filters):
        if filters:
            binarize = any(f['name'] == 'binarize' for f in filters)
        else:
            binarize = False
        data, self.len_output, self.original_order = \
            load_timeseries_from_file(source_file, binarize)
        return data

    def load_from_lines(self, lines, quantiles):
        self.quantiles = quantiles
        binarize = True if quantiles else False
        data, self.len_output, self.original_order = \
                load_timeseries_from_lines(lines, binarize)
        if binarize:
            data = self._apply_filter(data, 'binarize', None)
        self.data = data
        self.is_loaded = True

    def _load(self, dfile):
        super(Timeseries, self)._load(dfile)
        dset = dfile['data']
        self.len_output = dset.attrs['len_output']
        self.original_order = dfile['original_order'][...]
        try:
            self.quantiles = dfile['quantiles'][...]
        except KeyError:
            pass

    def _dump(self, dfile):
        super(Timeseries, self)._dump(dfile)
        dset = dfile['data']
        dset.attrs['len_output'] = self.len_output
        dfile.create_dataset('original_order', self.original_order.shape,
                             compression='gzip', data=self.original_order)
        if self.quantiles is not None:
            dfile.create_dataset('quantiles', self.quantiles.shape,
                                 compression='gzip', data=self.quantiles)

    def _apply_filter(self, data, name, params):
        if name == 'binarize':
            data, self.quantiles = binarize(data, self.len_output,
                                            self.quantiles)
        elif name == 'split':
            data, self.original_order = split(data, self.original_order,
                                              params['start'], params['end'])
        return data

    def to_mrnn_format(self):
        if not self.in_mrnn_format:
            new_order = np.isnan(self.data).sum(axis=(1,2)).argsort()
            self.original_order = self.original_order[new_order]
            self.data = self.data[new_order]
            self.data = utils.to_mrnn_shape(self.data)
            self.in_mrnn_format = True

    def get_training_data(self):
        self.to_mrnn_format()
        return self.data, self.len_output

    def get_predict_data(self):
        self.to_mrnn_format()
        return self.data, self.len_output, self.original_order

    @property
    def extra_params(self):
        return {'quantiles': self.quantiles}
