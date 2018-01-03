import numpy as np
from ersatz import aws
from .. import get_logger
from ..exception import ApiParamsError
from . images import ImageDataset 

DEBUG_FLAG = False


log = get_logger('ersatz.data.provider')


class CsvDataProvider(object):

    def __init__(self, train_datafile, test_datafile=None, valid_datafile=None,
                 output_len=0, shuffle=True, **kwargs):
        """
        output_len: number of columns to use as output from the end
        """

        log.info('CsvDataProvider created.')
        self.train_datafile = train_datafile
        self.test_datafile = test_datafile
        self.valid_datafile = valid_datafile
        self.output_len = output_len
        self.train_set_x = None
        self.train_set_y = None
        self.train_set_x_shape = None
        self.test_set_x = None
        self.test_set_y = None
        self.test_set_x_shape = None
        self.valid_set_x = None
        self.valid_set_y = None
        self.valid_set_x_shape = None
        self.shuffle = shuffle
        self.load()
        self.save_shapes()
        self.save_uniq_outputs_num()

    def load(self):
        log.info('Parsing and loading data in numpy array...')
        train_set = self.train_datafile
        test_set = self.test_datafile
        valid_set = self.valid_datafile
        self.train_set_x, self.train_set_y = self.split_in_out(train_set)
        self.test_set_x, self.test_set_y = self.split_in_out(test_set)
        self.valid_set_x, self.valid_set_y = self.split_in_out(valid_set)

    def save_shapes(self):
        self.train_set_x_shape = self.train_set_x.shape
        log.debug('Train X shape: ' + str(self.train_set_x_shape))
        if self.train_set_y is not None:
            log.debug('Train Y shape: ' + str(self.train_set_y.shape))
        if self.test_set_x is not None:
            self.test_set_x_shape = self.test_set_x.shape
            log.debug('Test X shape: ' + str(self.test_set_x_shape))
            if self.test_set_y is not None:
                log.debug('Test Y shape: ' + str(self.test_set_y.shape))
        else:
            log.debug('Test set not defined.')
        if self.valid_set_x is not None:
            self.valid_set_x_shape = self.valid_set_x.shape
            log.debug('Valid X shape: ' + str(self.valid_set_x_shape))
            if self.valid_set_y is not None:
                log.debug('Valid Y shape: ' + str(self.valid_set_y.shape))
        else:
            log.debug('Validation set not defined.')

    def save_uniq_outputs_num(self):
        if self.train_set_y is None:
            self.uniq_outputs_num = None
            self.labels = None
        else:
            # The following counts number of unique labels in dataset
            # for classification problems. Not, we are assuming that
            # if you only have classes 10 and 4 in your labeled dataset
            # the network that will be generated will still have 11 outputs
            # 10 for 1-10 + 1 for 0
            self.labels = np.unique(self.train_set_y)
            self.uniq_outputs_num = np.max(self.labels) + 1

    def make_scaled(self):
        self.train_set_x = self.scale(self.train_set_x)
        self.test_set_x = self.scale(self.test_set_x)
        self.valid_set_x = self.scale(self.valid_set_x)

    def scale(self, data):
        ''' data should be a 2d np array '''
        if data is not None and data.size != 0:
            return (data - np.min(data)) / (np.max(data) - np.min(data))
        return data

    def make_shared(self):
        self.train_set_x = self.share(self.train_set_x)
        self.test_set_x = self.share(self.test_set_x)
        self.valid_set_x = self.share(self.valid_set_x)
        if self.train_set_y is not None:
            self.train_set_y = self.share(self.train_set_y.flatten(), cast='int32')
        if self.test_set_y is not None:
            self.test_set_y = self.share(self.test_set_y.flatten(), cast='int32')
        if self.valid_set_y is not None:
            self.valid_set_y = self.share(self.valid_set_y.flatten(), cast='int32')

    def share(self, data, cast=None, borrow=True):
        # because of conflict with mrnn gpu initialization
        # we must import theano always in separate process
        import theano
        if data is None:
            return None
        shared_data = theano.shared(np.asarray(data, dtype=theano.config.floatX),
                                    borrow=borrow)
        if cast is not None:
            shared_data = theano.tensor.cast(shared_data, cast)
        return shared_data

    def split_in_out(self, dataset):
        if self.output_len and dataset is not None:
            return dataset[:,:-self.output_len], dataset[:,-self.output_len:]
        return dataset, None

    def split_train_set(self, train_set):
        size = train_set.shape[0]
        self.calc_slices(size)
        if self.data_slices is not None:
            train_set_alias = train_set[self.data_slices[0]]
            test_set = train_set[self.data_slices[1]]
            valid_set = train_set[self.data_slices[2]]
            return train_set_alias, test_set, valid_set
        return train_set, None, None

    def calc_slices(self, size):
        data_split = self.data_split
        if data_split is None:
            self.data_slices = None
            return
        if len(data_split) < 3:
            data_split.extend([0] * (3 - len(data_split)))
        if sum(data_split) != 100:
            self.data_slices = None
            raise ApiParamsError('Invalid value for data split %s' % data_split,
                                 show_to_user=True)
        train_high_mark = np.ceil(size / 100. * data_split[0])
        train_slice = slice(0, train_high_mark)
        test_high_mark = np.ceil(size / 100. * data_split[1]) + train_high_mark
        test_slice = slice(train_high_mark, test_high_mark)
        valid_high_mark = np.ceil(size / 100. * data_split[2]) + test_high_mark
        valid_slice = slice(test_high_mark, valid_high_mark)
        self.data_slices = [train_slice, test_slice, valid_slice]


class HDF5ImagesDataProvider(CsvDataProvider):
    def __init__(self, key, img_size=32, shuffle=True):
        self.key = key
        self.img_size = img_size
        if DEBUG_FLAG:
            f = key
        else:
            f = aws.S3Key(self.key).get()
        self.dataset = ImageDataset()
        self.dataset.load(f)
        self.data = self.dataset.data
        self.labels = self.dataset.labels
        self.label_list = self.labels.iterkeys()
        self.class_sizes = self.dataset.class_sizes

    def get_class_sizes(self):
        """Return a list of integers representing the number of elements per class
        in the dataset.
        """
        #return [self.labels[k] for k in self.label_list]
        return self.class_sizes

    def get_class_labels(self):
        """return the sorted list of labels"""
        return self.label_list

    def get_num_classes(self):
        return len(self.labels)

    def get_meta(self):
        self.metabatch = {
            'data_mean': np.zeros((self.img_size * self.img_size, 1)),
            'num_vis': self.img_size * self.img_size,
            'label_names': self.label_list
        }
        return self.metabatch

    def get_class_chunk(self, class_number, slice_):
        """Return a "chunk" of data, corresponding to a subset of the numpy
        array of images, with the given class_number and indexed by the
        given slice object.

        This returns identical output as the the corresponding 
        ArchivedImagesDataProvider method, but  doesn't iterate over images
        because the images are already in numpy form.

        Considerations:
        - We no longer maintain a list of image filenames in self.labels,
        instead we just store the class sizes, which is all the information
        we need to create the slice object which gets passed get_class_chunk.
        The slice object is applied directly to the self.data numpy nd_array.
        So what we need to do is modify the slice object with our knowledge
        of the given class's offset. **See TODO below
        - Assumes that the stored data hasn't been shuffled! Don't store shuffle!
        """
        cnt = self.class_sizes[class_number]
        index_offset = sum(self.class_sizes[:class_number])
        index_start = slice_.start + index_offset
        index_stop = index_start + min(cnt,slice_.stop)
        # if the chunk is supposed to cross class boundaries, replace line 219 w/ this:
        #index_stop = index_start + min(slice_.stop, sum(self.class_sizes[class_number:])
        slice_ = slice(index_start, index_stop)
        labels = np.array([class_number] * cnt).reshape((cnt, 1))
        return {'data': self.data[slice_], 'labels': labels}
        
        """
        Old Considerations:
        - The implementation of labels in the new hdf5 scheme is poorly defined
        at this point. The old ArchivedImagesDataProvider parsed filenames to
        extract image classes. 
        - Every time ArchivedImagesDataProvider was instantiated, it repeated
        the parse that should have been stored during DM_Worker's initial pass.
        
        Questions:
        - What is the appropriate hdf5 methodology for storing the class labels?
            Is it groups? Metadata attributes? A secondary dataset of
            label strings?
        - HDF5 features "chunking" of datasets for non-contiguous storage. Does
        this map to the data provider conception of chunks (of size 10,000) being
        sliced for gpu batch processing? Or is this just a naming overlap.
        """
