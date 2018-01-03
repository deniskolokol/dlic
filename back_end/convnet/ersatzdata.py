#coding: utf-8
from __future__ import division
import os
import sys
import numpy as np
from convdata import CIFARDataProvider
cwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(cwd, '..'))
from ersatz.data.cifar_provider import ArchivedImagesDataProvider


class ErsatzDataProvider(CIFARDataProvider):
    def __init__(self, data_dir, batch_range, init_epoch=1,
                 init_batchnum=None, dp_params={}, test=False):
        self.data_dir = data_dir
        self.curr_epoch = init_epoch
        self.dp_params = dp_params
        self.test = test
        self.data_dic = []
        self.batch_meta = None
        self.batch_range = None
        self.percents = batch_range[0]
        self.num_colors = 3
        self.img_size = self.dp_params['convnet'].img_size
        if test:
            self.idp = ArchivedImagesDataProvider(data_dir, self.img_size)
        else:
            self.idp = self.dp_params['convnet'].test_data_provider.idp

        self.create_batches()
        self.batch_meta = self.idp.get_meta()

        if init_batchnum is None or init_batchnum not in self.batch_range:
            init_batchnum = self.batch_range[0]
        self.batch_idx = self.batch_range.index(init_batchnum)
        self.curr_batchnum = init_batchnum

        # Subtract the mean from the data and make sure that both data and
        # labels are in single-precision floating point.
        data = None
        for d in self.data_dic:
            if data is None:
                data = d['data']
            else:
                data = np.hstack((data, d['data']))
        self.batch_meta['data_mean'] = self.data_mean = data.mean(axis=1).reshape((self.img_size**2 * 3, 1))

        for d in self.data_dic:
            # This converts the data matrix to single precision and
            # makes sure that it is C-ordered
            d['data'] = np.require((d['data'] - self.data_mean),
                                    dtype=np.single, requirements='C')
            d['labels'] = np.require(d['labels'].reshape((1, d['data'].shape[1])),
                                     dtype=np.single, requirements='C')

    def get_batch_range(self):
        return self.batch_range

    def shuffle_in_unison(self, a, b):
        assert a.shape[1] == b.shape[0]
        shuffled_a = np.empty(a.shape, dtype=a.dtype)
        shuffled_b = np.empty(b.shape, dtype=b.dtype)
        permutation = np.random.permutation(len(b))
        for old_index, new_index in enumerate(permutation):
            shuffled_a[:, new_index] = a[:, old_index]
            shuffled_b[new_index] = b[old_index]
        return shuffled_a, shuffled_b

    def create_batches(self):
        self.calc_test_percent()
        self.num_classes = self.idp.get_num_classes()
        self.get_batch_sizing()
        self.data_dic = []
        for batch_num in self.batch_range:
            data = labels = None
            batch_num -= 1
            for cls, sz in enumerate(self.batch_sizes):
                if (batch_num + 1) == self.batch_range[-1] and not self.test:
                    sl = slice(sz * batch_num, sz * batch_num + sz + 10000)
                else:
                    sl = slice(sz * batch_num, sz * batch_num + sz)
                chunk = self.idp.get_class_chunk(cls, sl)
                if data is None:
                    #from MRNN import rdb; rdb.set_trace()
                    data = chunk['data']
                    labels = chunk['labels']
                else:
                    data = np.hstack((data, chunk['data']))
                    labels = np.vstack((labels, chunk['labels']))
            data, labels = self.shuffle_in_unison(data, labels)
            self.data_dic.append({'data': data, 'labels': labels})

    def calc_test_percent(self):
        ## must be test_percent >= 50
        if self.test:
            self.test_percent = self.percents
        else:
            self.test_percent = 100 - self.percents

    def get_batch_sizing(self):
        """ calc number of cases of each class in batch, if sum of cases more
            than 10000 make more batches"""
        def get_percent(value, percent):
            return int(value * percent / 100) or 1

        class_sizes = self.idp.get_class_sizes()
        batch_sizes = ([get_percent(x, self.test_percent)
                        for x in class_sizes])
        mult = 1
        percent = self.test_percent
        while sum(batch_sizes) > 10000 and self.num_classes < 10000:
            mult += 1
            percent = self.test_percent / mult
            batch_sizes = ([get_percent(x, percent)
                            for x in class_sizes])
        self.batch_sizes = batch_sizes
        num_batches = np.floor(class_sizes[0] / batch_sizes[0]).astype(int)
        if self.test:
            self.batch_range = range(1, mult + 1)
        else:
            self.batch_range = range(mult + 1, num_batches + 1)
