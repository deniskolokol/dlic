from ..conf import settings
import h5py


class BaseDataset(object):
    def __init__(self):
        self.data = None
        self.is_loaded = False

    def load(self, dataset_file):
        """
        Unpack dataset from hdf5 file into self
        """
        with h5py.File(dataset_file, 'r') as f:
            self._load(f)
        self.is_loaded = True

    def save(self, dataset_file):
        """
        Save all dataset data into hdf5 file
        """
        assert self.is_loaded
        with h5py.File(dataset_file, 'w', libver='latest') as f:
            self._dump(f)

    def load_from_source(self, source_file, filters=None, **kwargs):
        """
        Load source data, apply filters and store dataset into self
        """
        self._filters = filters
        data = self._load_source(source_file, **kwargs)
        self.data = self._apply_filters_pipeline(data, filters)
        self.is_loaded = True

    def _apply_filters_pipeline(self, data, filters):
        """
        Applies filters in the defined order.
        """
        if not filters:
            return data
        filters_order = ('ignore', 'outputs', 'balance', 'permute', 'normalize',
                         'shuffle', 'merge', 'binarize', 'split',)
        for flt_name in filters_order:
            try:
                flt = [f for f in filters if f['name'] == flt_name][0]
                data = self._apply_filter(data, flt_name, flt)
            except:
                pass
        return data

    def _load(self, dfile):
        """
        Loads data from hdf5 into self.
        """
        dset = dfile['data']
        self.data = dset[...]
        self.source_data_type = dset.attrs['source_data_type']
        self.version = dset.attrs['version']

    def _dump(self, dfile):
        """
        Stores data from self to hdf5.
        """
        dset = dfile.create_dataset('data', self.data.shape,
                                    compression='gzip', data=self.data)
        dset.attrs['source_data_type'] = self.source_data_type
        dset.attrs['version'] = settings.DATASET_VERSION

    def _load_source(self, source_file):
        """
        Returns data from data file.
        """
        raise NotImplementedError()

    def _apply_filter(self, data, name, params):
        raise NotImplementedError()

    def get_training_data(self):
        """
        Returns all data which trainer need from dataset.
        """
        raise NotImplementedError()

    def get_predict_data(self):
        raise NotImplementedError()

    @property
    def extra_params(self):
        return {}
