import cStringIO
import numpy as np
from scipy import sparse
from . base import BaseDataset
from .formats import CsvDataFile
from ..aws import S3Key
from ..shared.fileutils import TempFile
from utils import ProcessCall, open_datafile
import json



def filter_merge(source, output, datas, dataset_class, filters=None):
    for key in datas:
        source_file = S3Key(key).get()
        dset = dataset_class() # so inheritors can override _load_source
        with_output = output is not None
        if filters:
            dset.load_from_source(source_file, filters)
            data = dset.data
        else:
            data = dset._load_source(source_file)
        source = np.vstack((source, data))
        if with_output:
            output = np.vstack((output, dset.output))
    return source, output


def filter_shuffle(source, output):
    rng = np.random.RandomState(777)
    rng.shuffle(source)
    rng.seed(777)
    if output is not None:
        rng.shuffle(output)
    return source, output


def filter_split(source, output, start, end):
    length = source.shape[0]
    start = int(round(length * (start / 100.0)))
    end = int(round(length * (end / 100.0)))
    split_source = source[start:end]
    if output is not None:
        output = output[start:end]
    return split_source, output


def filter_ignore(data, output, columns):
    data = np.delete(data, columns, axis=1)
    return data, output


def filter_output(data, columns):
    output = data[:, columns]
    if output.size == 0:
        return data, None
    else:
        return filter_ignore(data, output, columns)


def filter_permute(data, output, columns):
    delete_cols = []
    matrix = sparse.csr_matrix((data.shape[0], 1))
    for column in columns:
        cat = data[:, column].astype(int)
        indptr = range(cat.shape[0]+1)
        ones = np.ones(cat.shape[0])
        permut = sparse.csr_matrix((ones, cat, indptr))[:, 1:]
        try:
            matrix = sparse.hstack((matrix, permut))
            delete_cols.append(column)
        except ValueError:
            pass
    matrix = np.delete(matrix.toarray(), 0, axis=1)
    data = np.delete(data, delete_cols, axis=1)
    result = np.hstack((data, matrix))
    return result, output


def sample_over(data, distrib, classes_num, indices):
    count = np.max(distrib)
    result = np.empty((count * len(distrib) - len(data),) + data.shape[1:],
                      data.dtype)
    slices = np.concatenate(([0], np.cumsum(count - distrib)))
    for i in xrange(classes_num):
        where = np.random.choice(np.where(indices == i)[0], count - distrib[i])
        result[slices[i]:slices[i+1]] = data[where]
    return np.vstack((data, result))


def sample_under(data, distrib, classes_num, indices):
    count = np.min(distrib)
    where = np.empty((0,))
    for i in xrange(classes_num):
        idx = np.where(indices == i)[0]
        np.random.shuffle(idx)
        where = np.append(where, idx[:distrib[i] - count])
    return np.delete(data, where, axis=0)


def sample_uniform(data):
    out = data[:, -1].astype(int)
    distr = np.bincount(out)
    prob = 1 / distr[out].astype(float)
    prob /= prob.sum()
    sz = np.count_nonzero(distr) * distr.max()
    return data[np.random.choice(np.arange(len(data)), size=sz, p=prob)]


def filter_balance(data, output, sample):
    if output is None:
        raise Exception('Balancing can only be applied to the datasets with output!')
    data = np.hstack((data, output))
    output = output.astype(int)
    b = np.ascontiguousarray(output).view(
        np.dtype((np.void, output.dtype.itemsize * output.shape[1])))
    _, idx, indices = np.unique(b, return_inverse=True, return_index=True)
    classes = output[idx]
    distrib = np.bincount(indices)
    if sample == 'oversampling':
        result = sample_over(data, distrib, len(classes), indices)
    elif sample == 'undersampling':
        result = sample_under(data, distrib, len(classes), indices)
    elif sample == 'uniform':
        result = sample_uniform(data)
    return result[:, :np.negative(output.shape[1])], \
           result[:, np.negative(output.shape[1]):]


#TODO: this function need careful testing
def filter_normalize(data, norm_min_max=None):
    if norm_min_max is None:
        data_min = data.min(axis=0)
        data_max = data.max(axis=0)
    else:
        data_min, data_max = norm_min_max[0], norm_min_max[1]
        norm_min_max = np.vstack((data_min, data_max))
    delta = data_max - data_min
    delta[delta == 0] = 1
    data = (data - data_min) / delta
    # when we use min max values from dataset on user data from
    # load_from_lines
    data[data<0] = 0
    data[data>1] = 1
    return data, norm_min_max


class GeneralDataset(BaseDataset):
    def __init__(self):
        self.norm_min_max = None
        self.output = None
        self.filter_output = None
        self.columns = []
        self.error_lines = []
        self.source_data_type = "GENERAL"
        super(GeneralDataset, self).__init__()

    def load_from_source(self, source, **kwargs):
        target = kwargs.pop('target', None)
        if target is None:
            raise Exception('Target dataset not specified')
        with TempFile() as src:
            with open(src, 'w') as sf_:
                for line in open_datafile(source):
                    line += '\n'
                    sf_.write(line.replace('\n\n', '\n'))
            with TempFile() as conf:
                with open(conf, 'w') as tf_:
                    tf_.write(json.dumps(kwargs))
                proc = ProcessCall('csvstat', 'load', src, target, conf)
                meta, errors = proc.call()
        errors = json.loads('[%s]' % ','.join(errors.strip().split('\n')))
        for error in errors:
            if error['status'] == u'FATAL':
                raise Exception(error['descr'])
        return target

    def _load_source(self, source_file, **kwargs):
        csvdatafile = CsvDataFile(source_file, **kwargs)
        data = csvdatafile.load_to_ndarray(False)
        self.error_lines = csvdatafile.error_lines
        return data

    def load_from_lines(self, data, norm_min_max=None, **kwargs):
        self.norm_min_max = norm_min_max
        data = cStringIO.StringIO(data)
        csvdatafile = CsvDataFile(data, **kwargs)
        data = csvdatafile.load_to_ndarray(False)
        if norm_min_max:
            data = self._apply_filter(data, 'normalize', None)
        self.data = data
        self.error_lines = csvdatafile.error_lines
        self.is_loaded = True

    def _load(self, dfile):
        super(GeneralDataset, self)._load(dfile)
        if 'norm_min_max' in dfile:
            self.norm_min_max = dfile['norm_min_max'][...]
        if 'output' in dfile:
            self.output = dfile['output'][...]


    def _dump(self, dfile):
        super(GeneralDataset, self)._dump(dfile)
        if self.norm_min_max:
            dfile.create_dataset('norm_min_max', self.norm_min_max.shape,
                                 compression='gzip', data=self.norm_min_max)
        if self.output is not None:
            dfile.create_dataset('output', self.output.shape,
                                 compression='gzip', data=self.output)

    def adjust_columns(self, columns, columns_total):
        if not self.columns:
            return columns
        result = []
        current = np.sort(np.array(self.columns))
        for column in np.sort(np.array(columns)):
            col_no = column - np.where(current < column)[0].size
            if col_no < columns_total:
                result.append(col_no)
        return result

    def _apply_filter(self, data, name, params):
        if 'columns' in params:
            columns = sorted([int(x) for x in params['columns']])
            self.columns = self.adjust_columns(columns, data.shape[1])
        if name == 'ignore':
            data, self.output = filter_ignore(data, self.output, self.columns)
        elif name == 'outputs':
            self.filter_output = [params]
            data, self.output = filter_output(data, self.columns)
        elif name == 'permute':
            data, self.output = filter_permute(data, self.output, self.columns)
        elif name == 'merge':
            dataset_class = type(self)
            data, self.output = filter_merge(data, self.output, params['datas'], dataset_class, self.filter_output)
        elif name == 'split':
            data, self.output = filter_split(data, self.output, params['start'], params['end'])
        elif name == 'shuffle':
            data, self.output = filter_shuffle(data, self.output)
        elif name == 'normalize':
            data, self.norm_min_max = filter_normalize(data, self.norm_min_max)
        elif name == 'balance':
            data, self.output = filter_balance(data, self.output, params['sample'])
        else:
            raise Exception('No such filter %s' % name)
        return data

    def get_training_data(self):
        if self.output is None:
            return self.data
        return np.hstack((self.data, self.output))

    def get_predict_data(self):
        return self.data

    @property
    def extra_params(self):
        return {'norm_min_max': self.norm_min_max,
                'error_lines': self.error_lines}
