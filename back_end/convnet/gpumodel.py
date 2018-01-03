# Copyright (c) 2011, Alex Krizhevsky (akrizhevsky@gmail.com)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# 
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from time import time, asctime, localtime, strftime
from numpy import array, vstack
from util import *
from data import *
from options import *
from data import DataProvider, dp_types
import sys
import pika
import json
from os import linesep as NL
from ersatz import api
from ersatz.reporter import (RabbitReporterMixin, RabbitPipe,
                             logs_transformer, logs_saver)
from ersatz.rabbit import get_connection
from ersatz.misc import Tee


class ModelStateException(Exception):
    pass


# GPU Model interface
class IGPUModel(RabbitReporterMixin):
    def __init__(self, model_name, op, load_dic, filename_options=None, dp_params={}):
        # these are input parameters
        self.model_name = model_name
        self.op = op
        self.options = op.options
        self.load_dic = load_dic
        self.filename_options = filename_options
        self.dp_params = dp_params
        self.get_gpus()
        self.fill_excused_options()
        #assert self.op.all_values_given()

        self.initialize_stats_reporter()
        
        for o in op.get_options_list():
            setattr(self, o.name, o.value)

        # initialize training pipe
        routing_key = 'ensemble.%d.model.%d' % (self.ensemble_id, self.model_id)
        pre_hooks = [logs_transformer(self.model_id)]
        post_hooks = [logs_saver(self.model_id)]
        self.train_pipe = RabbitPipe(get_connection(),
                                     exchange_name='training_logs',
                                     exchange_type='topic',
                                     routing_key=routing_key,
                                     buffer_age=2,
                                     pre_hooks=pre_hooks,
                                     post_hooks=post_hooks)

        # capture stdout and stderr starting from instantiation
        sys.stdout = Tee('stdout', self.train_pipe)
        sys.stderr = Tee('stderr', self.train_pipe)

        # these are things that the model must remember but they're not input parameters
        if load_dic:
            self.model_state = load_dic["model_state"]
            self.save_file = self.options["load_file"].value
            if not os.path.isdir(self.save_file):
                self.save_file = os.path.dirname(self.save_file)
        else:
            self.model_state = {}
            if filename_options is not None:
                self.save_file = model_name + "_" + '_'.join(['%s_%s' % (char, self.options[opt].get_str_value()) for opt, char in filename_options]) + '_' + strftime('%Y-%m-%d_%H.%M.%S')
            self.model_state["train_outputs"] = []
            self.model_state["test_outputs"] = []
            self.model_state["epoch"] = 1
            self.model_state["batchnum"] = self.train_batch_range[0]

        self.init_data_providers()
        if load_dic: 
            self.train_data_provider.advance_batch()
            
        # model state often requries knowledge of data provider, so it's initialized after
        try:
            self.init_model_state()
        except ModelStateException, e:
            print e
            sys.exit(1)
        for var, val in self.model_state.iteritems():
            setattr(self, var, val)
            
        self.import_model()
        self.init_model_lib()

        # TODO: confirm where to get ensemble and model IDs
        # initialize training pipe
        # ensemble_id = api_message.get('ensemble', 0)
        # model_id = api_message['models'][0].get('id', 0)
        # routing_key = 'ensemble.%d.model.%d' % (ensemble_id, model_id)

        # pre_hooks = [logs_transformer(model_id)]
        # post_hooks = [logs_saver(model_id)]
        # self.train_pipe = RabbitPipe(get_connection(),
        #                              exchange_name='training_logs',
        #                              exchange_type='topic',
        #                              routing_key=routing_key,
        #                              buffer_age=2,
        #                              pre_hooks=pre_hooks,
        #                              post_hooks=post_hooks)

    def import_model(self):
        print "========================="
        print "Importing %s C++ module" % ('_' + self.model_name)
        self.libmodel = __import__('_' + self.model_name) 
                   
    def fill_excused_options(self):
        pass
    
    def init_data_providers(self, dp_type=None):
        if dp_type is not None:
            self.dp_type = dp_type
            self.train_batch_range = self.test_batch_range
        self.dp_params['convnet'] = self
        self.dp_params['img_size'] = self.img_size
        try:
            self.test_data_provider = DataProvider.get_instance(
                self.data_path, self.test_batch_range,
                type=self.dp_type, dp_params=self.dp_params, test=True)
            self.train_data_provider = DataProvider.get_instance(
                self.data_path, self.train_batch_range,
                self.model_state["epoch"], self.model_state["batchnum"],
                type=self.dp_type, dp_params=self.dp_params, test=False)
        except DataProviderException, e:
            print "Unable to create data provider: %s" % e
            self.print_data_providers()
            sys.exit()
        if hasattr(self.train_data_provider, 'get_batch_range'):
            self.train_batch_range = self.train_data_provider.get_batch_range()
        if hasattr(self.test_data_provider, 'get_batch_range'):
            self.test_batch_range = self.test_data_provider.get_batch_range()
        
    def init_model_state(self):
        pass
       
    def init_model_lib(self):
        pass
    
    def start(self):
        if self.test_only:
            self.test_outputs += [self.get_test_error()]
            self.print_test_results()
            sys.exit(0)
        self.train()

        # cleanup
        sys.stdout.close()
        sys.stderr.close()
        self.train_pipe.close()

    def train(self):
        print "========================="
        print "Training %s" % self.model_name
        self.op.print_values()
        print "========================="
        self.print_model_state()
        print "Running on CUDA device(s) %s" % ", ".join("%d" % d for d in self.device_ids)
        print "Current time: %s" % asctime(localtime())
        print "Saving checkpoints to %s" % os.path.join(self.save_path, self.save_file)
        print "========================="
        next_data = self.get_next_batch()
        self.begin_train_time = self.last_report_time = time()
        while self.epoch <= self.num_epochs:
            data = next_data
            self.epoch, self.batchnum = data[0], data[1]
            self.print_iteration()
            sys.stdout.flush()
            
            compute_time_py = time()
            self.start_batch(data)
            
            # load the next batch while the current one is computing
            next_data = self.get_next_batch()
            
            batch_output = self.finish_batch()
            self.train_outputs += [batch_output]
            self.print_train_results()

            batch_num = self.batchnum - self.train_batch_range[0] + 1
            if batch_num == len(self.train_batch_range) and \
                    (self.epoch % self.testing_freq == 0 or
                     self.epoch % self.saving_freq == 0 or
                     self.epoch == self.num_epochs):
                self.sync_with_host()
                self.test_outputs += [self.get_test_error()]
                self.print_test_results()
                self.print_test_status()
                save = (self.epoch % self.saving_freq == 0 or
                        self.epoch == self.num_epochs)
                self.conditional_save(save)

            self.print_train_time(time() - compute_time_py)
        self.cleanup()

    def cleanup(self):
        self.close_stats_reporter()
        sys.exit(0)
        
    def sync_with_host(self):
        self.libmodel.syncWithHost()
            
    def print_model_state(self):
        pass
    
    def get_num_batches_done(self):
        return len(self.train_batch_range) * (self.epoch - 1) + self.batchnum - self.train_batch_range[0] + 1
    
    def get_next_batch(self, train=True):
        dp = self.train_data_provider
        if not train:
            dp = self.test_data_provider
        return self.parse_batch_data(dp.get_next_batch(), train=train)
    
    def parse_batch_data(self, batch_data, train=True):
        return batch_data[0], batch_data[1], batch_data[2]['data']
    
    def start_batch(self, batch_data, train=True):
        self.libmodel.startBatch(batch_data[2], not train)
    
    def finish_batch(self):
        return self.libmodel.finishBatch()
    
    def print_iteration(self):
        print "\t%d.%d..." % (self.epoch, self.batchnum),
    
    def print_train_time(self, compute_time_py):
        print "(%.3f sec)" % (compute_time_py)
    
    def print_train_results(self):
        batch_error = self.train_outputs[-1][0]
        if not (batch_error > 0 and batch_error < 2e20):
            print "Crazy train error: %.6f" % batch_error
            self.cleanup()

        print "Train error: %.6f " % (batch_error),

    def print_test_results(self):
        batch_error = self.test_outputs[-1][0]
        print "%s\t\tTest error: %.6f" % (NL, batch_error),

    def print_test_status(self):
        status = (len(self.test_outputs) == 1 or self.test_outputs[-1][0] < self.test_outputs[-2][0]) and "ok" or "WORSE"
        print status,
        
    def conditional_save(self, save=False):
        batch_error = self.test_outputs[-1][0]
        if batch_error > 0 and batch_error < self.max_test_err:
            self.save_state(save)
        else:
            print "\tTest error > %g, not saving." % self.max_test_err,
    
    def aggregate_test_outputs(self, test_outputs):
        test_error = tuple([sum(t[r] for t in test_outputs) / (1 if self.test_one else len(self.test_batch_range)) for r in range(len(test_outputs[-1]))])
        return test_error
    
    def get_test_error(self):
        next_data = self.get_next_batch(train=False)
        test_outputs = []
        while True:
            data = next_data
            self.start_batch(data, train=False)
            load_next = not self.test_one and data[1] < self.test_batch_range[-1]
            if load_next: # load next batch
                next_data = self.get_next_batch(train=False)
            test_outputs += [self.finish_batch()]
            if self.test_only: # Print the individual batch results for safety
                print "batch %d: %s" % (data[1], str(test_outputs[-1]))
            if not load_next:
                break
            sys.stdout.flush()
            
        return self.aggregate_test_outputs(test_outputs)
    
    def set_var(self, var_name, var_val):
        setattr(self, var_name, var_val)
        self.model_state[var_name] = var_val
        return var_val
        
    def get_var(self, var_name):
        return self.model_state[var_name]
        
    def has_var(self, var_name):
        return var_name in self.model_state

    def update_accuracy_stats(self):
        batches_len = len(self.train_batch_range)
        if not hasattr(self, 'api_train_outputs'):
            temp = [[x[0]['logprob'][0], 1 - x[0]['logprob'][1]]
                    for x in self.model_state['train_outputs']]
            api_train_outputs = array(temp).reshape((-1, batches_len, 2))\
                    .mean(axis=1)
            self.api_train_outputs = api_train_outputs
        else:
            saved_len = self.api_train_outputs.shape[0] * batches_len
            temp = [[x[0]['logprob'][0], 1 - x[0]['logprob'][1]]
                    for x in self.model_state['train_outputs'][saved_len:]]
            api_train_outputs = array(temp).reshape((-1, batches_len, 2))\
                    .mean(axis=1)
            self.api_train_outputs = vstack((self.api_train_outputs,
                                             api_train_outputs))

        self.api_test_outputs = [[x[0]['logprob'][0], 1 - x[0]['logprob'][1], x[2]]
                for x in self.model_state['test_outputs']]

    def report_stats(self, save=False):
        def get_label_names():
            labels = self.train_data_provider.batch_meta['label_names']
            return [str(x).strip('/').rsplit('/', 1)[-1].lower() for x in labels]

        if not self.load_file or save:
            modeldata = [{'model_state': self.model_state, 'op': self.op},
                         self.train_data_provider.batch_meta]
            s3_data = aws_upload_modeldata(modeldata, self.load_file, self.model_id)
            if s3_data is None:
                print 'Can\'t upload model data to s3'
                return
            self.load_file = s3_data
        test_accuracy = 1 - self.model_state['test_outputs'][-1][0]['logprob'][1]
        train_accuracy = 1 - self.model_state['train_outputs'][-1][0]['logprob'][1]
        self.update_accuracy_stats()
        cur_time = time()
        payload = {
                        'model': self.model_id,
                        'model_name': 'CONV',
                        'data': {'iteration': self.model_state['epoch'],
                                 'test_accuracy': test_accuracy,
                                 'train_accuracy': train_accuracy,
                                 'train_outputs': self.api_train_outputs,
                                 'test_outputs': self.api_test_outputs,
                                 'label_names': get_label_names(),
                                 'time': cur_time - self.last_report_time,
                                 'total_time': cur_time - self.begin_train_time},
                        's3_data': self.load_file,
                        'queue_key': self.queue_key
                  }

        ok = api.post('/api/stats/', payload)
        if ok:
            self.last_report_time = cur_time
        else:
            print "Api respond with not 200 status, stop training"
            sys.exit(100)

    def close_stats_reporter(self):
        if self.stats_reporter:
            self.stats_reporter.basic_cancel()
            self.stats_reporter.close()
            self.stats_reporter.connection.close()
            self.stats_reporter = None
        else:
            print "No active IGPUModel stats reporter."

    def report_stats2(self, save=False):
        def get_label_names():
            labels = self.train_data_provider.batch_meta['label_names']
            return [str(x).strip('/').rsplit('/', 1)[-1].lower() for x in labels]

        if not self.load_file or save:
            modeldata = [{'model_state': self.model_state, 'op': self.op},
                         self.train_data_provider.batch_meta]
            s3_data = aws_upload_modeldata(modeldata, self.load_file, self.model_id)
            if s3_data is None:
                print 'Can\'t upload model data to s3'
                return
            self.load_file = s3_data
        test_accuracy = 1 - self.model_state['test_outputs'][-1][0]['logprob'][1]
        train_accuracy = 1 - self.model_state['train_outputs'][-1][0]['logprob'][1]
        self.update_accuracy_stats()
        cur_time = time()
        payload = {
            'model': self.model_id,
            'model_name': 'CONV',
            'data': {'iteration': self.model_state['epoch'],
                     'test_accuracy': test_accuracy,
                     'train_accuracy': train_accuracy,
                     'train_outputs': self.api_train_outputs.tolist(),
                     'test_outputs': self.api_test_outputs,
                     'label_names': get_label_names(),
                     'time': cur_time - self.last_report_time,
                     'total_time': cur_time - self.begin_train_time},
            's3_data': self.load_file,
            'queue_key': self.queue_key
        }

        # client is waiting, serve em first
        self.stats_publish(json.dumps(payload))

        # then persist stats
        ok = api.post('/api/stats/', payload)
        if ok:
            self.last_report_time = cur_time
        else:
            print "Api respond with not 200 status, stop training"
            sys.exit(100)

    def save_state(self, save=False):
        for att in self.model_state:
            if hasattr(self, att):
                self.model_state[att] = getattr(self, att)
        #self.report_stats(save)
        self.report_stats2(save)

    @staticmethod
    def load_checkpoint(load_dir):
        return aws_load_modeldata(load_dir)

    @staticmethod
    def get_options_parser():
        op = OptionsParser()
        op.add_option("f", "load_file", StringOptionParser, "Load file", default="", excuses=OptionsParser.EXCLUDE_ALL)
        op.add_option("train-range", "train_batch_range", RangeOptionParser, "Data batch range: training")
        op.add_option("test-range", "test_batch_range", RangeOptionParser, "Data batch range: testing")
        op.add_option("data-provider", "dp_type", StringOptionParser, "Data provider", default="default")
        op.add_option("test-freq", "testing_freq", IntegerOptionParser, "Testing frequency", default=25)
        op.add_option("epochs", "num_epochs", IntegerOptionParser, "Number of epochs", default=500)
        op.add_option("data-path", "data_path", StringOptionParser, "Data path")
        op.add_option("save-path", "save_path", StringOptionParser, "Save path")
        op.add_option("max-filesize", "max_filesize_mb", IntegerOptionParser, "Maximum save file size (MB)", default=5000)
        op.add_option("max-test-err", "max_test_err", FloatOptionParser, "Maximum test error for saving")
        op.add_option("num-gpus", "num_gpus", IntegerOptionParser, "Number of GPUs", default=1)
        op.add_option("test-only", "test_only", BooleanOptionParser, "Test and quit?", default=0)
        op.add_option("zip-save", "zip_save", BooleanOptionParser, "Compress checkpoints?", default=0)
        op.add_option("test-one", "test_one", BooleanOptionParser, "Test on one batch at a time?", default=1)
        op.add_option("gpu", "gpu", ListOptionParser(IntegerOptionParser), "GPU override", default=OptionExpression("[-1] * num_gpus"))
        return op

    @staticmethod
    def print_data_providers():
        print "Available data providers:"
        for dp, desc in dp_types.iteritems():
            print "    %s: %s" % (dp, desc)
            
    def get_gpus(self):
        self.device_ids = [get_gpu_lock(g) for g in self.op.get_value('gpu')]
        if GPU_LOCK_NO_LOCK in self.device_ids:
            print "Not enough free GPUs!"
            sys.exit()
        
    @staticmethod
    def parse_options(op):
        try:
            load_dic = None
            batch_meta = None
            options = op.parse()
            if options["load_file"].value_given:
                load_dic, batch_meta = IGPUModel.load_checkpoint(options["load_file"].value)
                old_op = load_dic["op"]
                old_op.merge_from(op)
                op = old_op
            op.eval_expr_defaults()
            return op, load_dic, batch_meta
        except OptionMissingException, e:
            print e
            op.print_usage()
        except OptionException, e:
            print e
        except UnpickleError, e:
            print "Error loading checkpoint:"
            print e
        sys.exit()
