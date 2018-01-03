#!/usr/bin/python
import rdb
from twisted.internet import protocol, reactor, defer
import socket
import opt.utils.nonlin
from math import ceil
from numpy import zeros, ones
import numpy as np
import gnumpy as g
import random, os
import cPickle
import pandas as pd

random.seed()

class DataRequest():
    def __init__(self):
        self.chunks = []

    def connect(self, host, port):
        self.sock = socket.create_connection((host,port))
        self.connectionMade()
    
    def connectionMade(self):
        instructions = ','.join([str(self.factory.timesteps), str(self.factory.batch_size), self.factory.subset])
        self.sock.send(instructions)

        length = None
        while True:
            data = self.sock.recv(4096)
            if not data: break
            self.chunks.append(data)

        self.connectionLost()

    def connectionLost(self):

        header = self.chunks[0].split(',')[:-1]
        destination = header[0]
        self.chunks[0] = self.chunks[0].split(',')[-1]
        array = self.chunks = ''.join(self.chunks)

        if destination=='v':
            array = cPickle.loads(self.chunks)
            self.factory.stock_data_object.validation_data = array
            self.factory.stock_data_object.validation_data_np = \
                    self.factory.stock_data_object.valid_to_numpy()
        else:
            length = int(header[1])
            self.factory.columns = int(header[3])
            array = np.fromstring(self.chunks)

            self.factory.columns = len(array)/length/self.factory.timesteps
            array = array.reshape((length, self.factory.timesteps, self.factory.columns)) 

            if destination=='t': #train
                self.factory.stock_data_object.train_data = array
                self.factory.stock_data_object.v = self.factory.stock_data_object.V \
                    = self.factory.stock_data_object.train_data.shape[2]-4
            elif destination=='T': #test
                self.factory.stock_data_object.test_data = array

        if self.factory.stock_data_object.train_data is not None and \
            self.factory.stock_data_object.test_data is not None and \
            self.factory.stock_data_object.validation_data is not None:
                self.factory.stock_data_object.calculate_number_of_batches()
        
        self.chunks = []

        del self

class DataRequestFactory():
    protocol = DataRequest

    def __init__(self, timesteps, columns, batch_size, subset, stock_data_object):
        self.timesteps = timesteps
        self.columns = columns
        self.batch_size = batch_size
        self.subset = subset
        self.stock_data_object = stock_data_object
        dr = DataRequest()
        dr.factory = self
        dr.connect('localhost','8008')

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed'

    def clientConnectionLost(self, connector, reason):
        print 'connection lost'

class StockData(object):
    """
    This class is designed to replace opt.d.lang.ContiguousText
    by implementing its protocol (interface) but reading input from elsewhere
    """
    def __init__(self, 
                 data, 
                 T, 
                 batch_size, 
                 train_prob=0.8,
                 T_warmup=10, 
                 T_frac=0.9):
        """
        data: 2D numpy array of floats read from input file
        T: int, number of Time steps for each sample
        batch_size: int
        train_prob: float 0..1, how large part of data will be used for training
        T_warmup: int
        T_frac: float 0..1, used for true_T
        """


        self.out_nonlin = opt.utils.nonlin.Softmax

        self.file_array = data
        self.train_prob = train_prob
        self.batch_size = batch_size
        self.T = T
        assert T >= 2*T_warmup
        self.true_T = min(int(T*T_frac), T-T_warmup) # whichever eats up more: either T_warmup, or T*T_frac
        self.T_warmup = T_warmup
        self.batch_fn = self
        self.train_mem = {}

        self.times_called = 0

        self.train_data = None
        self.test_data = None
        self.validation_data = None

        #self.load_stock_data()
        self.create_test_train_data()
        #self.calculate_number_of_batches()


        # Number of features

        # with sigmoid nonlinearity, len(self.O) != len(self.V)
        self.o = self.O = 4
        # Length of third dimension - in wikipedia it's 
        # length of 0000010000 vector
#        self.o = self.O = self.v = self.V = 1

    def load_train_data(self):
        drf = DataRequestFactory(100, 38, 15000, 'train', self)

    def load_test_data(self):
        drf = DataRequestFactory(100, 38, 5000, 'test', self)

    def load_validation_data(self):
        drf = DataRequestFactory(100, 38, 10000, 'validate', self)

    def create_test_train_data(self):
        """
        Split data array into test/train subarrays
        """
        self.load_train_data()
        if self.test_data is None:
            self.load_test_data()
        if self.validation_data is None:
            self.load_validation_data()

    def valid_to_numpy(self):
        """
        This is supposed to take the validation pandas object and return a big ol' batch
        in numpy form representing the data to be fed to the model...
        """
        import re
        columns = []
        for c in self.validation_data[0].columns:
            if re.search('\d$', c) is not None: columns.append(c)
        
        data = []
        for ticker in self.validation_data:
            t = ticker.reindex_axis(columns, axis=1)
            data.append(t.values)

        return_data = np.array(data)
        try:
            assert len(return_data.shape) == 3
        except:
            import rdb; rdb.set_trace()
        return return_data

    def calculate_number_of_batches(self):
        """
        Create self.train_batches and self.test_batches
        based on batch size and input data size
        """
        real_batch_size = self.batch_size # float(self.batch_size * self.true_T)
        num_train_batches = int(ceil(
            self.train_data.shape[0] / real_batch_size
        ))
        
        num_test_batches = int(ceil(
            self.test_data.shape[0] / real_batch_size
               ))

        if self.validation_data_np.shape[0] < real_batch_size:
            num_valid_batches = self.validation_data_np.shape[0]
        else:
            num_valid_batches = int(ceil(
                len(self.validation_data_np) / real_batch_size
                   ))

        print "BATCHES: %d / %d / %d" % (num_train_batches, num_test_batches, num_valid_batches)

        self.train_batches = range(num_train_batches)
        self.test_batches = [-x-1 for x in range(num_test_batches)]
        self.valid_batches = range(num_valid_batches)
        self.forget()

    def create_batch(self, batch_id, core_V_small, seed=[]):
        """
        Fill core_V_small with batch number b
        batch_id: int
        core_V_small: zeros((T+1, batch_size, self.V)) 
        seed: [int int int] array containing seed to use instead of random
        return: [int int int] seed

        Called from self.__call__. This function actually creates the batch,
        rest of code in __call__ is mostly boilerplate
        """
        T = self.T
        had_seed = (len(seed) > 0)
        if not had_seed:
            seed = list()

        random.seed()
        
        for b in xrange(self.batch_size):
            if not had_seed:
                row = np.random.randint(len(self.train_data) - T - 1)
                seed.append(row) # store for caching
            else:
                row = seed[b] # we have already been at this batch so let's recall what we did back then

            core_V_small[:T, b, :] = self.train_data[row, :T, :] 

        return seed
    

    def forget(self):
        self.train_mem.clear()

    def cycle_data(self, defer_result=False):
        from termcolor import colored
        print colored("Rotating data", "red")
        del self.train_data
        self.create_test_train_data()

        #self.calculate_number_of_batches()
        #self.forget()


    def get_valid_batch(self, X):
        """
        Given number, return a validation batch
        """
        if X >= self.validation_data_np.shape[0]:
            raise Exception('You asked for ticker #'+str(X)+' but there are only '+\
                str(self.validation_data_np.shape[0]) + ' tickers available in your validation set.')

        M = None
        T = self.T

        tickers = [X for x in xrange(len(self.validation_data_np[X])-T)]

        offset_counters = [x for x in xrange(len(self.validation_data_np[X])-T)]

        batch_size = len(tickers)
        from numpy import zeros
        core_V = zeros((T, batch_size, self.V))
        core_O = zeros((T, batch_size, self.O))
        core_M = zeros((T, batch_size, 4))

        core_V_small = zeros((T, batch_size, self.V+self.O))
            
        for b, ticker, offset_counter in zip(xrange(batch_size), tickers, offset_counters):
            try:
                core_V_small[:T, b, :] = self.validation_data_np[ticker, offset_counter:offset_counter+T, :] 
                #core_V_small[:T, b, :] = self.validation_data_np[ticker][offset_counter:offset_counter+T, :]
            except:
                import rdb; rdb.set_trace()

        # Copy core_V_small onto core_V and core_O
        core_V[:] = core_V_small[:,:,:-4]
        core_O[:] = core_V_small[:,:,-4:]

        if M is None:
            core_M[-self.true_T:, :, :] = 1
        else:
            # the point is, M is known during training. But during test time,
            # right at the beginning, we want M to cover the start as well. 
            # Alright, cool! Let's proceed. 
            core_M[:] = M 

        try:
            Vs = map(g.garray, core_V)
        except:
            import rdb; rdb.set_trace()
        Os = map(g.garray, core_O)
        Ms = map(g.garray, core_M)

        return Vs, Os, Ms

    def __call__(self, x):
        """
        Return batch number x
        x: int
        return: V,O,P arrays
        """
        M = None # TODO: probably not always true

        if x < 0:
            # test
            batch_id = x-1
            mode = 'test'
        else:
            # train
            batch_id = x
            mode = 'train'

        T = self.T
        batch_size = self.batch_size
        
        from numpy import zeros
        core_V = zeros((T, batch_size, self.V))
        core_O = zeros((T, batch_size, self.O))
        core_M = zeros((T, batch_size, 4))

        core_V_small = zeros((T, batch_size, self.V+self.O))

        # fill core_V_small with data
        if mode == 'train' and (batch_id in self.train_mem):
#            print ("seeding - batch_id %d / " % batch_id) , self.train_mem
            self.create_batch(batch_id, core_V_small, self.train_mem[batch_id])
        else:
#            print "Random seed for batch %d" % batch_id
            self.train_mem[batch_id] = self.create_batch(batch_id, core_V_small)
#            print self.train_mem[batch_id]

        # Copy core_V_small onto core_V and core_O
        core_V[:] = core_V_small[:,:,:-4]
        core_O[:] = core_V_small[:,:,-4:]

        if M is None:
            core_M[-self.true_T:, :, :] = 1
        else:
            # the point is, M is known during training. But during test time,
            # right at the beginning, we want M to cover the start as well. 
            # Alright, cool! Let's proceed. 
            core_M[:] = M 

        Vs = map(g.garray, core_V)
        Os = map(g.garray, core_O)
        Ms = map(g.garray, core_M)

        return Vs, Os, Ms

    # Interface implementation
    def size(self, b):
        V,O,M = b
        assert len(V)==len(O)==len(M)

        # allow for fractional batch sizes, in case our test set doesn't quite have everything. Awesome. 
        return sum([m.sum() for m in M]) / float(self.true_T)
