#!/usr/bin/python
from termcolor import colored
import numpy as np
import random
from ersatz.mrnn.opt.utils import nonlin
from ersatz.mrnn import gnumpy as g
from ersatz.mrnn.util import shmem_as_ndarray2
from ersatz import get_logger

log = get_logger('generic 3d data')

random.seed()

class Generic3dData(object):
    def __init__(self, T, v, o, batch_size, dp_data,
            out_nonlin=nonlin.Softmax, data_sizes=None,
            num_timesteps=0):
        """
        data: 2D numpy array of floats read from input file
        T: int, number of Time steps for each sample
        batch_size: int
        train_prob: float 0..1, how large part of data will be used for training
        T_warmup: int
        T_frac: float 0..1, used for true_T
        """
        self.out_nonlin = out_nonlin
        self.T = T
        self.batch_size = batch_size
        # because num_timesteps can be much bigger than real data
        # length, we selecting num_timesteps only in case if it smaller
        # then real T
        self.true_T = min(num_timesteps, T)
        self.batch_fn = self
        self.train_mem = {}
        self.times_called = 0
        self.train_data = None
        self.test_data = None
        self.validation_data = None
        self.dp_data = dp_data
        self.batches_info = {}


        if data_sizes:
            # TODO fix this we don't use this
            self.train_batches = range(max(data_sizes['grad'],
                                           data_sizes['gn'],
                                           data_sizes['line_search']))
            self.test_batches = [-1-x for x in range(data_sizes['test'])]
            # we don't really use
            # valid set right now, we should
            self.valid_batches = range(data_sizes['line_search'])

        self.create_test_train_data()
        self.o = self.O = o
        self.v = self.V = v

    def sig(self, batch_id):
        """
        Return "an id" for each batch. Used to ensure that different
        minibatches are actually different.
        """
        ans = self.batches_info[batch_id]['sig']
        if ans is None:
            ans = 0
            batch = self(batch_id)
            for t in range(min(3, len(batch[0]))):
                z = batch[0][-t]
                ans += (z[:-1]*z[1:]).sum()
            self.batches_info[batch_id]['sig'] = ans
        return ans

    def size(self, b):
        V,O,M = b
        assert len(V)==len(O)==len(M)
        # allow for fractional batch sizes,
        # in case our set doesn't quite have everything. Awesome.
        return sum([m.sum() for m in M]) / float(self.true_T)

    def forget(self):
        print colored('FORGETTING', 'red')

    def cycle_data(self, defer_result=False):
        print colored("Rotating data", "red")

    def create_test_train_data(self):
        """
        Split data array into test/train subarrays
        """
        log.debug('loading train data...')
        self.train_data = shmem_as_ndarray2(self.dp_data['train']['shmem'],
                                            shape=self.dp_data['train']['shape'])
        self.train_batches = range(self.dp_data['train']['num_batches'])
        for b in self.train_batches:
            self.batches_info[b] = {'sig': None, 'T': None}
        log.debug('done')
        if self.test_data is None:
            log.debug('loading test data...')
            self.test_data = shmem_as_ndarray2(self.dp_data['test']['shmem'],
                                                shape=self.dp_data['test']['shape'])
            self.test_batches = [-x-1 for x in range(self.dp_data['test']['num_batches'])]
            for b in self.test_batches:
                self.batches_info[b] = {'sig': None, 'T': None}
            log.debug('done')
        if self.validation_data is None:
            log.debug('loading valid data...')
            #self.validation_data = self.factory.get_data('validate')
            #self.valid_batches = range(len(self.validation_data))
            log.debug('done')

    def __call__(self, x):
        """
        Return batch number x
        x: int
        return: V,O,P arrays
        """


        if x < 0:
            mode = 'test'
        else:
            mode = 'train'
        batch_id = x


        batch = self.create_batch(mode, batch_id)

        T = batch.shape[0]
        Vs = []
        Os = []
        Ms = []
        for t, timestep in enumerate(batch):
            num_features = timestep.shape[1]
            timestep = timestep[~np.isnan(timestep)].reshape((-1, num_features))
            if timestep.size == 0:
                # if timestep contains only nans, then we at the end of
                # samples and in this batch no one sample has this
                # timestep, stop processing next timesteps
                break
            batch_size = timestep.shape[0]
            v = timestep[:, :-self.O]
            o = timestep[:, -self.O:]
            if mode == 'train' and t < T - self.true_T:
                m = g.zeros((batch_size, 1))
            else:
                m = g.ones((batch_size, 1))
            Vs.append(g.garray(v))
            Os.append(g.garray(o))
            Ms.append(m)
        return Vs, Os, Ms

    def create_batch(self, mode, batch_id):
        if mode == 'train':
            batch_size = self.dp_data['train']['batch_size']
            data = self.train_data
        else:
            batch_size = self.dp_data['test']['batch_size']
            data = self.test_data
            batch_id = -batch_id - 1
        return data[:, batch_size*batch_id:batch_size*(batch_id+1), :]
