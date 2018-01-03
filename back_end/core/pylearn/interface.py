import numpy as np
import cPickle
from collections import Counter
import theano.tensor as T
from theano import function
from pylearn2.train_extensions import TrainExtension
from pylearn2.termination_criteria import TerminationCriterion
from pylearn2.datasets.dense_design_matrix import DenseDesignMatrix
from pylearn2.training_algorithms.learning_rule import MomentumAdjustor
from pylearn2.training_algorithms.sgd import ExponentialDecay
from pylearn2.models.mlp import Sigmoid, RectifiedLinear
from pylearn2.models.maxout import Maxout, MaxoutConvC01B
from ersatz import get_logger
from ersatz.exception import DataFileError


log = get_logger('ersatz.pylearn.interface')

def shared_value(monitor, channel):
    return monitor.channels[channel].val_shared.get_value()


class SparseInitPercentMixin(object):
    def get_si(self):
        if not hasattr(self, '_sparse_init_percent'): # locals() is bad
            self._sparse_init_percent = self.__dict__['sparse_init']
            del self.__dict__['sparse_init']
        if self._sparse_init_percent is None:
            return None
        sparse_init = np.ceil(self.input_dim * self._sparse_init_percent / 100)
        return int(sparse_init) or 1 # at least 1

    def set_si(self, val):
        self._sparse_init_percent = val

    def del_si(self):
        del self._sparse_init_percent

    sparse_init = property(get_si, set_si, del_si)


class _RectifiedLinear(SparseInitPercentMixin, RectifiedLinear):
    pass


class _Sigmoid(SparseInitPercentMixin, Sigmoid):
    pass


class _Maxout(SparseInitPercentMixin, Maxout):
    pass


class _MaxoutConvC01B(SparseInitPercentMixin, MaxoutConvC01B):
    pass


def fix_accuracy_format(data):
    train_max, test_max = [max(y) for y in zip(*[x[1:3] for x in data])]
    if train_max > 1 or test_max > 1:
        for val in data:
            val[1] = val[1] / 100.
            val[2] = val[2] / 100.
    return data


class StatReporter(TrainExtension):

    def __init__(self, runner, resume=False, resume_data=None,
                 save_freq=1, *args, **kwargs):
        self.save_freq = save_freq
        self.runner = runner
        self.first_iter = True
        if resume:
            self.train_outputs = resume_data['train_outputs']
            # old models store accuracy as percentage
            # like 80.0 for 80% right classified samples
            # for it we search such accuracy and convert to range [0, 1]
            self.train_outputs = fix_accuracy_format(self.train_outputs)
        else:
            self.train_outputs = []

    def on_monitor(self, model, dataset, algorithm):
        if self.first_iter:
            #if this is first iteration of new training, this will be called
            #before training start
            #if model was resumed, first call will be with last epoch,
            #which already reported
            self.first_iter = False
            return

        log.debug('Collecting model data and stats...')
        modeldata, stats = self.collect_stats(model, dataset, algorithm)
        if self.is_save_conditions(model, algorithm):
            modeldata = cPickle.dumps(modeldata, protocol=cPickle.HIGHEST_PROTOCOL)
            upload_modeldata = True
        else:
            modeldata = None,
            upload_modeldata = False
        self.runner.report_stats(modeldata, stats, upload_modeldata=upload_modeldata)

    def is_save_conditions(self, model, algorithm):
        cnd1 = not algorithm.termination_criterion.continue_learning(model)
        cnd2 = self.epoch == 1
        cnd3 = self.epoch % self.save_freq == 0
        return cnd1 or cnd2 or cnd3

    def collect_stats(self):
        raise NotImplementedError


def _confusion_f1_score(predicted, actual, labels):
    """
        To compute f1 score correctly for binary labels
        we would need to know which label is positive. Since
        there is no such information a weighted average is always
        computed instead. If we had the information it would be a
        matter of returning f1score[index_of_positive_class]
    """
    confusion = {}
    true_pos, false_pos, false_neg = [np.zeros((len(labels), ), dtype=np.int) for _ in range(3)]

    for i, klass in enumerate(labels):
        confusion[int(klass)] = cnt = Counter(predicted[actual==klass].tolist())

        true_pos[i] = cnt[klass]
        false_neg[i] = sum(cnt.itervalues()) - true_pos[i]
        false_pos[i] = np.sum(predicted[actual != klass] == klass)

    with np.errstate(divide = 'ignore', invalid = 'ignore'):
        precision = np.divide(true_pos.astype(np.float), true_pos + false_pos)
        recall = np.divide(true_pos.astype(np.float), true_pos + false_neg)

        precision[(true_pos + false_pos) == 0] = 0.0
        recall[(true_pos + false_neg) == 0] = 0.0

        f1score = np.divide(2*precision*recall, precision + recall)
        f1score[(precision + recall) == 0] = 0.0

    support = true_pos + false_neg

    #assuming all support cannot be 0
    weighted = np.average(f1score, weights = support)

    return confusion, weighted


class MLPStatReporter(StatReporter):

    def __init__(self, model, *args, **kwargs):
        super(MLPStatReporter, self).__init__(*args, **kwargs)
        self.compile_confusion_matrix(model)

    def compile_confusion_matrix(self, model):
        self.cm_klasses = None
        Xb = model.get_input_space().make_batch_theano()
        ymf = model.fprop(Xb)
        res = T.argmax(ymf, axis=1)
        self.cm_fn = function([Xb],[res])


    def get_confusion_matrix_f1(self, model, algorithm):
        def _get_confusion_matrix_f1(dataset, actual):
            dataset = algorithm.monitoring_dataset[dataset]
            if dataset.X_topo_space is None:
                data_specs = None
            else:
                data_specs = (dataset.X_topo_space, 'features')
            batches = dataset.iterator(mode='sequential',
                                       batch_size=algorithm.batch_size,
                                       data_specs=data_specs)
            predicted = None
            for batch in batches:
                rval = self.cm_fn(batch)[0]
                if predicted is None:
                    predicted = rval
                else:
                    predicted = np.hstack((predicted, rval))

            return _confusion_f1_score(predicted, actual, self.cm_klasses)

        y_train = algorithm.monitoring_dataset['train'].y.argmax(axis=1)
        y_test = algorithm.monitoring_dataset['valid'].y.argmax(axis=1)
        if self.cm_klasses is None:
            self.cm_klasses = np.unique(np.hstack((y_train, y_test)))
        confusion_train, f1_train = _get_confusion_matrix_f1('train', y_train)
        confusion_test, f1_test = _get_confusion_matrix_f1('valid', y_test)
        return confusion_train, confusion_test, f1_train, f1_test

    def collect_stats(self, model, dataset, algorithm):
        monitor = model.monitor
        self.epoch = monitor._epochs_seen
        _acc = lambda rmin, rmax, rmean: (abs(rmean - rmax) - (rmean - rmin)) / ((rmax - rmin) / 2)
        if self.runner.model['out_nonlin'] == 'LINEARGAUSSIAN':
            train_accuracy = _acc(shared_value(monitor, 'train_y_row_norms_min'),
                                  shared_value(monitor, 'train_y_row_norms_max'),
                                  shared_value(monitor, 'train_y_row_norms_mean'))
            valid_accuracy = _acc(shared_value(monitor, 'valid_y_row_norms_min'),
                                  shared_value(monitor, 'valid_y_row_norms_max'),
                                  shared_value(monitor, 'valid_y_row_norms_mean'))
            train_loss = shared_value(monitor, 'train_y_mse')
            valid_loss = shared_value(monitor, 'valid_y_mse')
        else:
            train_accuracy = 1 - shared_value(monitor, 'train_y_misclass')
            valid_accuracy = 1 - shared_value(monitor, 'valid_y_misclass')
            train_loss = shared_value(monitor, 'train_y_nll')
            valid_loss = shared_value(monitor, 'valid_y_nll')

        self.train_outputs.append([
                self.epoch,
                train_accuracy,
                valid_accuracy,
                train_loss,
                valid_loss,
                shared_value(monitor, 'learning_rate'),
                shared_value(monitor, 'momentum'),
                shared_value(monitor, 'valid_y_row_norms_mean'),
                shared_value(monitor, 'valid_y_col_norms_mean'),
                max(shared_value(monitor, 'monitor_seconds_per_epoch'), .01)
            ])
        outputs_header = ['iteration', 'train_accuracy', 'test_accuracy',
                          'train_loss', 'test_loss', 'learning_rate',
                          'momentum', 'last_layer_row_norms_mean',
                          'last_layer_col_norms_mean', 'iteration_time']
        modeldata = {
            'model': model,
            'epoch': self.epoch,
            'train_outputs': self.train_outputs,
            'outputs_header': outputs_header,
        }
        cm_train, cm_test, f1_train, f1_test = self.get_confusion_matrix_f1(model, algorithm)
        stats = {
            'iteration': self.train_outputs[-1][0],
            'train_accuracy': self.train_outputs[-1][1],
            'test_accuracy': self.train_outputs[-1][2],
            'train_outputs': self.train_outputs,
            'outputs_header': outputs_header,
            'confusion_matrix': cm_test,
            'confusion_matrix_train': cm_train,
            'f1score_train': f1_train,
            'f1score_test': f1_test
        }
        return modeldata, stats


class AutoEncoderStatReporter(StatReporter):

    def collect_stats(self, model, dataset, algorithm):
        monitor = model.monitor
        self.epoch = monitor._epochs_seen
        self.train_outputs.append([
                self.epoch,
                monitor.channels['objective'].val_shared.get_value()])
                #max(monitor.channels['monitor_seconds_per_epoch'].val_shared.get_value(), .01)])
        outputs_header = ['iteration', 'cost', 'iteration_time']
        modeldata = {
            'model': model,
            'epoch': self.epoch,
            'train_outputs': self.train_outputs,
            'outputs_header': outputs_header,
        }
        stats = {
            'iteration': self.train_outputs[-1][0],
            'train_accuracy': 0.1,
            'test_accuracy': 0.1,
            'train_outputs': self.train_outputs,
            'outputs_header': outputs_header,
        }
        return modeldata, stats


class MaxEpochNumber(TerminationCriterion):

    def  __init__(self, max_epochs):
        self._max_epochs = max_epochs

    def continue_learning(self, model):
        return model.monitor._epochs_seen < self._max_epochs


def create_dense_design_matrix(x, y=None, num_classes=None):
    if y is None:
        return DenseDesignMatrix(X=x)

    if num_classes is None:
        return DenseDesignMatrix(X=x, y=y)

    y = y.reshape((-1, ))
    one_hot = np.zeros((y.shape[0], num_classes), dtype='float32')
    for i in xrange(y.shape[0]):
        one_hot[i, y[i]] = 1.
    return DenseDesignMatrix(X=x, y=one_hot)


def create_2d_dense_design_matrix(x, y, num_classes=None, axes=['b', 0, 1, 'c']):
    sq_size = int(np.sqrt(x.shape[1]))
    if sq_size ** 2 != x.shape[1]:
        raise DataFileError('Can\'t convert input data to 2d space.',
                            show_to_user=True)
    topo_view = x.reshape(x.shape[0], sq_size, sq_size, 1)

    def dimshuffle(b01c):
        default = ('b', 0, 1, 'c')
        return b01c.transpose(*[default.index(axis) for axis in axes])

    one_hot = np.zeros((y.shape[0], num_classes), dtype='float32')
    y = y.reshape((-1, ))
    for i in xrange(y.shape[0]):
        one_hot[i, y[i]] = 1.
    y = one_hot

    topo_view = topo_view.reshape(topo_view.shape[0], sq_size, sq_size, 1)

    return DenseDesignMatrix(topo_view=dimshuffle(topo_view), y=y, axes=axes)


class LearningRateUpdate(ExponentialDecay):

    def __init__(self, decay_factor, final, current_iter):
        super(LearningRateUpdate, self).__init__(decay_factor, final)
        self._count = current_iter
        self._base_lr = None

    def __call__(self, algorithm):
        if self._base_lr is None:
            self._base_lr = algorithm.learning_rate.get_value()
        super(LearningRateUpdate, self).__call__(algorithm)


class MomentumUpdate(MomentumAdjustor):

    def __init__(self, start, stop, final, current_iter):
        super(MomentumUpdate, self).__init__(final, start, stop)
        self._count = current_iter
