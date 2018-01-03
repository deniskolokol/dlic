#!/usr/bin/python
import gc
import os
import json
import math
import uuid
import subprocess
from collections import Counter
import numpy as np
from termcolor import colored
from . import aws, get_logger, api
from .conf import settings
from .mrnn import gnumpy as g
from .mrnn.opt.utils import nonlin
from .mrnn.opt.m.rnn.mrnn import MRNN
from .mrnn.memory import get_max_gnumpy_memory
from .data.dataset import get_dataset
from .data.timeseries import Timeseries
from .data import utils as data_utils
from .mrnn.util import grab_gpu_boards
from .data import dataset as dataset_module
from .shared.cifar import BatchWriter


log = get_logger('predictor')


class LoadModelException(Exception):
    pass


def extend_with_nans(batches, shape_0=None):
    size = shape_0 if shape_0 is not None else batches[0].shape[0]
    for i in range(1, len(batches)):
        delta = np.tile(np.nan, (size - batches[i].shape[0], batches[i].shape[1]))
        batches[i] = np.vstack((batches[i], delta))
    return np.array(batches)


def remove_nans(data, is_argmax=True):
    temp = []
    for sample in data:
        temp.append([t for t in sample if not np.isnan(t).all()])
    return temp


class Predictor(object):

    def __init__(self, ensemble, predicts, queue_key, dataset,
                 quantiles, options, **kwargs):
        self.ensemble = ensemble
        self.queue_key = queue_key
        self.quantiles = quantiles
        self.dataset = dataset
        self.input_data = []
        self.models = [(m['iteration_id'], m['model_id'], self.load_model(**m))
                for m in predicts]
        self.init_gpu()
        gc.collect()

    def init_gpu(self):
        gpu_id = grab_gpu_boards()[0]
        g.board_id_to_use = gpu_id
        g._init_gpu()
        g.max_memory_usage = get_max_gnumpy_memory()

    def sort_as_original(self, data):
        return [x for (_, x) in sorted(zip(self.original_order, data))]

    def predict(self, input_data):
        pre_list = []
        predicts_results = []
        self._load_data(input_data)

        for (iteration_id, model_id, W) in self.models:
            print '==========', W.model_name, '=========='

            sig = W.out_nonlin
            H, results = W.forward_pass(self.input_data)[-2:]
            results = extend_with_nans([sig(x).as_numpy_array() for x in results])
            results = data_utils.to_normal_shape(results)
            results = self.sort_as_original(results)
            H = self.sort_as_original(H[1:])
            pre_list.append(results)
            results = remove_nans(results)
            predicts_results.append({
                'iteration': iteration_id,
                'output': results,
                'hidden_activations': H
            })

        avg_pre = np.array(pre_list).mean(axis=0)
        avg_pre = remove_nans(avg_pre)
        print 'Pre Activation Avg. Result: ', avg_pre
        print 'Results', predicts_results
        return {
                'ensemble_prediction': avg_pre,
                'predictions': predicts_results,
               }

    def load_mrnn(self, model_id, data, out_nonlin):
        NN_np1 = json.loads(data)
        X_np1 = np.array(NN_np1['X'])
        h1 = NN_np1['h']
        f1 = NN_np1['f']
        v1 = NN_np1['v']
        o1 = NN_np1['o']
        print 'Model %s is now loaded.' % model_id
        W = MRNN(v1, h1, f1, o1,
                hid_nonlin = nonlin.Tanh,
                out_nonlin = nonlin.get(out_nonlin))
        W = W.unpack(X_np1)
        W.model_name = 'MODEL %s' % model_id
        return W

    def load_model(self, model_id, model_name, s3_data, out_nonlin, **kwargs):
        data = aws.get_data(s3_data)
        if model_name == 'MRNN':
            return self.load_mrnn(model_id, data, out_nonlin)
        raise LoadModelException("Unavailable model name %s for model id %s" %
                (model_name, model_id))

    def _load_data(self, input_data):
        input_data = input_data.strip().split('\n')
        dataset = Timeseries()
        dataset.load_from_lines(input_data,
                                quantiles=self.dataset['quantiles'])
        data, _, self.original_order = dataset.get_predict_data()
        self.to_gnumpy(data)

    def to_gnumpy(self, data):
        for t, timestep in enumerate(data):
            num_features = timestep.shape[1]
            timestep = timestep[~np.isnan(timestep)].reshape((-1, num_features))
            self.input_data.append(g.garray(timestep))


class RunEnsemblePredictor(Predictor):

    def __init__(self, ensemble, predicts, queue_key, quantiles,
                 dataset, options, data_split=None, **kwargs):
        self.ensemble = ensemble
        self.queue_key = queue_key
        self.input_data = []
        self.input_only = kwargs.get('INPUT_ONLY', False)
        dataset = get_dataset(dataset)
        data, len_output, self.original_order = dataset.get_predict_data()
        if len_output:
            data, self.output_data = data[:,:,:-len_output], data[:,:,-len_output:]
        else:
            self.output_data = None
        self.to_gnumpy(data)
        self.models = [(m['iteration_id'], m['model_id'], self.load_model(**m))
                for m in predicts]
        del data
        self.init_gpu()
        gc.collect()

    def get_test_dataset(self, data, data_split):
        data_split = [int(math.floor(len(data) * perc / 100.0))
                           for perc in data_split]
        rng = np.random.RandomState(777) # same seed as in data provider
        rng.shuffle(data)
        return data[-data_split[1]:]

    def get_confusion_matrix(self, actual, predicted, mask):
        mask = mask.flatten()
        predicted = predicted.flatten()[mask==False]
        actual = actual.flatten()[mask==False]
        cm_klasses = np.unique(np.hstack((actual, predicted)))
        confusion = {}
        for klass in cm_klasses:
            confusion[int(klass)] = Counter(predicted[actual==klass].tolist())
        return confusion

    def to_str(self, data):
        return '\n'.join(';'.join(','.join(str(x) for x in timestep)
                                  for timestep in sample) for sample in data)

    def run_ensemble(self):
        pre_list = []
        iteration_ids = []
        models_ids = []
        for (iteration_id, model_id, W) in self.models:
            print '==========', W.model_name, '=========='

            sig = W.out_nonlin
            results = W.forward_pass(self.input_data)[4]

            pre_activation_results = extend_with_nans([sig(x).as_numpy_array()
                                                       for x in results])
            pre_list.append(pre_activation_results)
            iteration_ids.append(iteration_id)
            models_ids.append(model_id)

        avg_pre = np.array(pre_list).mean(axis=0)
        #if self.input_only:
        predicted_results = []
        for iteration_id, model_id, results in zip(iteration_ids, models_ids, pre_list):
            results = data_utils.to_normal_shape(results)
            results = self.sort_as_original(results)
            results = remove_nans(results)
            results = self.to_str(results)
            s3_key = '/download/predict/result/%s/ensemble-%s-iteration-%s.ts.gz'
            s3_key = s3_key % (uuid.uuid4(), self.ensemble, iteration_id)
            results = aws.save_as_s3_file(results, s3_key)
            predicted_results.append({
                'iteration': iteration_id,
                'output': results
            })
        avg = data_utils.to_normal_shape(avg_pre)
        avg = self.sort_as_original(avg)
        avg = remove_nans(avg)
        s3_key = '/download/predict/result/%s/avg-ensemble-%s-iterations-%s.ts.gz'
        s3_key = s3_key % (uuid.uuid4(), self.ensemble,
                           '-'.join(str(x) for x in iteration_ids))
        avg = self.to_str(avg)
        avg = aws.save_as_s3_file(avg, s3_key)
        return {'predictions': predicted_results, 'ensemble_prediction': avg}
        #else:
            ## for mask we selecting mean for reducing dim like argmax reduce
            ## but with mean we don't loose nan
            #mask = np.isnan(self.output_data.mean(axis=2))
            #actual = self.output_data.argmax(axis=2)
            #predict = avg_pre.argmax(axis=2)

            #confusion_matrix = self.get_confusion_matrix(actual, predict, mask)
            #each_timestep_acc = np.ma.masked_array(predict == actual, mask).mean(1)
            #weights = np.logical_not(mask).astype(int).sum(1)
            #dataset_acc = np.average(each_timestep_acc, weights=weights)
            #print dataset_acc
            #data = {
                #'run_ensemble_results': each_timestep_acc,
                #'dataset_accuracy': dataset_acc,
                #'confusion_matrix': confusion_matrix
            #}
        #return data


class PredictLifeSim(Predictor):
    def predict(self, input_data):
        self._load_data(input_data)
        results = []
        for (predict_id, model_id, W) in self.models:
            print 'Predicting ', W.model_name
            sig = W.out_nonlin
            result = W.forward_pass(self.input_data)
            results.append([sig(output) for output in result[4]])
        return results


def get_data_options_test(message_data, predict):
    test_dset = dataset_module.get_dataset(message_data['dataset'])
    data_path = dataset_module.prepare_dataset_file_dir(message_data['dataset']['key']).parent
    bw = BatchWriter(data_path, img_size=predict['model_params']['img_size'])
    bw.prepare_training(None, test_dset)
    return bw.get_data_options_test()


def predict_convnet(message_data):
    #simple interaction with convnet, better construct and run it from code,
    #but for beginning it ok
    predicts = message_data['predicts']
    # mkdirs
    data_path = settings.WORKING_DIR.child('predict',
                                           str(message_data['ensemble']),
                                           'data',
                                           str(message_data['train_ensemble_id']))
    data_path.mkdir(parents=True)
    exe_base = ['python', os.path.join(settings.CONVNET, 'shownet.py')]
    if message_data.get('input_data'):
        aws.save_to_file(message_data['input_data'], data_path.child('data_batch_999'))
        exe_base += [
            '--data-dir=' + data_path,
            '--test-range=999',
        ]
    else:
        # for now we only support one model per prediction
        exe_base += get_data_options_test(message_data, predicts[0])
    for predict in predicts[:1]:
        exe = exe_base[:]
        exe += [
            '-f', predict['s3_data'],
            '--show-preds=probs',
            '--queue-key=' + message_data['queue_key'],
            '--iteration-id=' + str(predict['iteration_id']),
            '--ensemble-id=' + str(message_data['ensemble'])
        ]
        print ' '.join(exe)
        proc = subprocess.Popen(exe, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print line.strip()
        if proc.poll() != 0:
            error = proc.stderr.read().strip()
            print colored(error, 'red')
            params = {'ensemble': message_data['ensemble'],
                      'traceback': error,
                      'error': 'Prediction error',
                      'queue_key': message_data['queue_key'],
                      'state': 'ERROR',
                      'time': 0}
            api.post('/api/predict-ensemble/status/', params)
        else:
            print colored('training finished.', 'blue')


# a note re: memory management on the GPU
# first of all, GPU is going to have some set amount of memory (say, 1.5 gigs).
# When you put data on the GPU, it tries to assign it as a contiguous block of
# memory.  So, you don't want to use all 1.5 gigs of memmory typically.

# You put data onto the GPU as soon as it becomes a garray.  Transfer from cpu
# to gpu is slow, so the rule is:
# if it's a simple operation on lots of data (matrix multiply/dot product primarily) then
# it makes sense to use GPU.  However, if you're multiplying a 5x5 matrix, it doesn't
# make sense because there is overhead associated with starting up the gpu operation.

# loading all the models onto the same GPU, then rotating data in batches onto and off of
# the gpu is a good strategy compared to the alternative of loading more data onto the gpu at once
# then iterating through your list of models, loading each one onto the GPU and then running
# through the data.  However, as it stands, if the models won't fit on a single GPU, it will crash
# it's important to check this in many places in ersatz, and it currently doesn't do any of
# that intelligent checking/memory management.

# this is also important because it is just as bad to use TOO MUCH memory (which just crashes the
# program) as it is to use TOO LITTLE memory, which makes poor use of available resources
# and makes ersatz unnecessarily slow.  The algos being used are already slow in theory...

# In order to load then clear gpu memory, you want to do something like this:
#     w = np.array([[1.,1.,0.,1.],[0.,1.,0.,1.]]) # numpy array, on cpu
#     x = g.garray(w) # you just copied the data from w onto GPU, you'll see GPU mem usage go up
#     y = g.dot(x,x.transpose()) # This operation happens on GPU. On a bigger array, it makes more sense.
#     z = y.asarray() # Now you've copied the result back to CPU
#     del x
#     del y
#     g.free_reuse_cache() # clears any data on the GPU that no longer has a reference to it (eg, x and y)
#                          # if you watch mem usage on the gpu, you'll see it lower at this point
# When we move to amazon, this is going to be particularly important because they're kind of slow
# and expensive machines for what you're getting (dual or quad teslas, i forget which)
# fortunately, teslas have more memory, so perhaps the hit you get from moving to a virtualized
# solution can be made up for by the ability to load more stuff onto each GPU at once.

# an additional consideration with multiGPU systems (which will be every system that ersatz workers
# run on...): It seems multiprocessing is the best way to do it currently.  Essentially, you
# start a separate process, then import gnumpy, grabbing a different GPU for each process.
# a manager process supervises.  As far as I can tell, the current limitations of this:
# you need to load the whole model onto the GPU (so model size ends up being this constant). Batch size
# you can adjust, and you can use "functional mini-batches" (used in the data class, you notice that there
# are batches and then there are the functional minibatches (eg, range(20), each index represents functional
# mini batch))

# but notice further down... I first sort the data into lists of lists (these are the batches)
# i then feed each batch to the GPU (which already has the models loaded on it).  The model
# runs through this data, I move the results back to CPU, free the space that the data was
# using up, and load more data onto it.  I rinse and repeat.

# before you were simply loading all the data on, but this is an assumption that can never be
# made.

# note, that this concept of "batches" only matters for learning.  That is, you compute
# the gradients (matrix of partial derivitives of the error with respect to inputs) on
# some "batch" of examples.  This models the general "surface" of the data, and you then
# use that information to figure out how to adjust the existing model weights.

# when you actually use the model, you don't need to compute any gradients, you've theoretically
# already "learned" how to make sense of the data, so now you can feed in batches one at a time.

# what would *really* be cool would be a system where you could do learning on pieces of the
# model at once and have a distributed system.  Then, there would be no limit on the size
# of models you could experiment with.  This is partially what they were trying to do with
# distbelief at google (which if I remember correctly was able to take advantage of the idea
# of partial connectivity found in convolutional nets and basically able to distribute the non-locally
# connected nodes across a CPU cluster (i'm not sure if google has gpu clusters... they don't seem to
# based on the research they've been publishing...))

# anyway, that's what I've got.  Also, much to my disappointment, model averaging doesn't seem to
# work in general.  I tried various schemes: average activations then put in softmax, softmax each
# activation then average the predictions, etc.  They all net out about the same, and it still
# fails to acheive higher accuracy than the best model in the ensemble.  This defeats the whole
# purpose... for reference, with experiments I did yesterday, there were 5 models in the ensemble,
# best model was 46.93%, min was 28.67%, simple mean (IE, average for all models) was 39.49%, the
# ensemble with averaging got 45.48%  So better than a simple expected average, but worse than
# the best score.
