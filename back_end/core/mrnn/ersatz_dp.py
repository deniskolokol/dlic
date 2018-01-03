##############################################################
#
#    This file contains the dataprovider for ersatz
#    It downloads a file from S3, converts it to a numpy
#    array and serves random batches of it on request
#    to other processes or servers
#
##############################################################
from multiprocessing import Array
from ..data import dataset
from .. import get_logger
from .util import shmem_as_ndarray2

log = get_logger('ersatz_dp')

class DP(object): # Data Provider Factory, not Double Penetration Factory...

    def __init__(self, params):
        self.train_dataset = params.get('train_dataset')
        self.test_dataset = params.get('test_dataset')
        self.valid_dataset = params.get('valid_dataset')

    def load_data(self):
        train, test, valid = dataset.load(self.train_dataset,
                                          self.test_dataset,
                                          self.valid_dataset)
        self.binary_train_data, self.len_output = train
        self.binary_test_data = None if test is None else test[0]
        self.binary_valid_data = None if valid is None else valid[0]

    def create_view(self):
        shmem_train_data = Array('f', self.binary_train_data.size)
        self._train_data = shmem_as_ndarray2(shmem_train_data,
                                             shape=self.binary_train_data.shape)
        self._train_data[:] = self.binary_train_data
        shmem_test_data = Array('f', self.binary_test_data.size)
        self._test_data = shmem_as_ndarray2(shmem_test_data,
                                       shape=self.binary_test_data.shape)
        self._test_data[:] = self.binary_test_data
        return {
            'train': {
                'shmem': shmem_train_data,
                'shape': self.binary_train_data.shape,
            },
            'test': {
                'shmem': shmem_test_data,
                'shape': self.binary_test_data.shape,
            }
        }
