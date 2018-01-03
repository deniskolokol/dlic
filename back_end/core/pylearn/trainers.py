import math
import traceback
from ersatz.exception import ApiParamsError
from .interface import (MLPStatReporter, AutoEncoderStatReporter,
                        MomentumUpdate, LearningRateUpdate,
                        _RectifiedLinear, _Sigmoid, _Maxout, _MaxoutConvC01B,
                        create_dense_design_matrix, MaxEpochNumber,
                        create_2d_dense_design_matrix)
import pylearn2
from pylearn2.train import Train
from pylearn2.models.mlp import (MLP, Softmax, LinearGaussian,
                                 mean_of_targets, beta_from_targets)
from pylearn2.training_algorithms.sgd import SGD
from pylearn2.costs.mlp.dropout import Dropout
from pylearn2.costs.autoencoder import MeanSquaredReconstructionError
from pylearn2.models.autoencoder import DenoisingAutoencoder
from pylearn2.corruption import BinomialCorruptor
from pylearn2.space import Conv2DSpace


def make(constructor, params):
    params = params.copy()
    try:
        del params['type']
    except KeyError:
        pass
    try:
        return constructor(params)
    except:
        traceback.print_exc()
        raise ApiParamsError(original_traceback=traceback.format_exc())


def construct_layers(model_params, dataset, out_nonlin):
    def add_maxout_conv_layer(params):
        params['kernel_shape'] = [params['kernel_shape'], params['kernel_shape']]
        params['pool_shape'] = [params['pool_shape'], params['pool_shape']]
        params['pool_stride'] = [params['pool_stride'], params['pool_stride']]
        params['num_channels'] = params['num_units']
        del params['num_units']
        return _MaxoutConvC01B(**params)

    def add_maxout_layer(params):
        return _Maxout(**params)

    def add_sigmoid_layer(params):
        return _Sigmoid(**params)

    def add_rectified_linear(params):
        return _RectifiedLinear(**params)

    layers = []
    constructor = {'maxout': add_maxout_layer,
                   'maxout_convolution': add_maxout_conv_layer,
                   'sigmoid': add_sigmoid_layer,
                   'rectified_linear': add_rectified_linear}
    for params in model_params['layers']:
        layers.append(make(constructor[params['type']], params))

    if out_nonlin == 'LINEARGAUSSIAN':
        layer = LinearGaussian(init_beta=beta_from_targets(dataset),
                               min_beta=1., max_beta=100., beta_lr_scale=1.,
                               layer_name='y', irange=.005,
                               dim=dataset.y.shape[1],
                               init_bias=mean_of_targets(dataset))
    else:
        layer = Softmax(max_col_norm=1.9365, layer_name='y',
                        n_classes=dataset.y.shape[1], irange=.005)
    layers.append(layer)
    return layers


def construct_update(model_params, resume=False, resume_data=None):
    update_callbacks = []
    extensions = []

    def custom_momentum(params):
        if params.get('constant'):
            return
        current_iter = 0
        if resume:
            current_iter = resume_data['epoch']
        ext = MomentumUpdate(start=params['start'],
                             stop=params['stop'] + 1,
                             final=params['final'],
                             current_iter=current_iter)
        extensions.append(ext)

    def custom_lr(params):
        if params.get('constant'):
            return
        current_iter = 0
        if resume:
            current_iter = resume_data['epoch']
        ext = LearningRateUpdate(decay_factor=params['decay_factor'],
                                 final=params['final'],
                                 current_iter=current_iter)
        update_callbacks.append(ext)

    params = model_params['learning_rate']
    if params:
        make(custom_lr, params)
    params = model_params['momentum']
    if params:
        make(custom_momentum, params)
    return update_callbacks, extensions


def get_batches_per_iter(model_params, train_dataset):
        percent = int(model_params['percent_batches_per_iter'])
        assert 0 < percent <= 100
        total_batches = math.ceil(train_dataset.X.shape[0] /
                                  float(model_params['batch_size']))
        batches_per_iter = math.ceil(total_batches * percent / 100.)
        return batches_per_iter


class BaseTrainer(object):
    pass


class MLPTrainer(BaseTrainer):
    def __init__(self, runner, model_params, resume=False,
                 resume_data=None, s3_data=None, **kwargs):        
        self.model_params = model_params
        self.out_nonlin = runner.model['out_nonlin']
        if self.out_nonlin == 'LINEARGAUSSIAN':
            outputs_num = None
            cost = None
        else:
            outputs_num = runner.dp.uniq_outputs_num
            cost = self.get_cost_fn()
        dataset = self.construct_datasets(runner.dp.train_set_x,
                                          runner.dp.train_set_y,
                                          outputs_num)
        valid_dataset = self.construct_datasets(runner.dp.test_set_x,
                                                runner.dp.test_set_y,
                                                outputs_num)
        if resume:
            model = self.resume_model(model_params, resume_data)
            lr_init = model_params['learning_rate']['init'] / (model_params['learning_rate']['decay_factor'] ** model.monitor.get_batches_seen())
        else:
            model = self.new_model(model_params, dataset=dataset)
            lr_init = model_params['learning_rate']['init']

        batches_per_iter = get_batches_per_iter(model_params, dataset)
        termination_criterion = MaxEpochNumber(model_params['maxnum_iter'])
        update_callbacks, extensions = construct_update(model_params,
                                                        resume, resume_data)
        algorithm = SGD(learning_rate=lr_init,
                        init_momentum=model_params['momentum']['init'],
                        monitoring_dataset={'valid': valid_dataset,
                                            'train': dataset},
                        cost=cost,
                        termination_criterion=termination_criterion,
                        update_callbacks=update_callbacks,
                        batches_per_iter=batches_per_iter)
        self.train_obj = Train(dataset=dataset,
                               model=model,
                               algorithm=algorithm,
                               extensions=extensions)
        ext = MLPStatReporter(model, runner, resume=resume,
                              resume_data=resume_data,
                              save_freq=model_params['save_freq'])
        self.train_obj.extensions.append(ext)

    def get_cost_fn(self):
        return None

    def train(self):
        self.train_obj.main_loop()

    def resume_model(self, model_params, resume_data):
        model = resume_data['model']
        model = pylearn2.monitor.push_monitor(model, 'monitor_validation', True)
        return model

    def new_model(self, model_params, dataset):
        layers = construct_layers(model_params, dataset, self.out_nonlin)
        model = MLP(batch_size=model_params['batch_size'], layers=layers,
                    nvis=dataset.X.shape[1])
        return model

    def construct_datasets(self, x, y, num_outputs):
        return create_dense_design_matrix(x=x, y=y, num_classes=num_outputs)


class MaxOutTrainer(MLPTrainer):
    def get_cost_fn(self):
        return Dropout()


class MaxOutConvTrainer(MLPTrainer):
    def get_cost_fn(self):
        return Dropout(input_include_probs={'h0': .8}, input_scales={'h0': 1.})

    def construct_datasets(self, x, y, num_outputs):
        return create_2d_dense_design_matrix(
            x=x, y=y, num_classes=num_outputs, axes=['c', 0, 1, 'b']
        )

    def new_model(self, model_params, dataset):
        layers = construct_layers(model_params,
                                  dataset.y.shape[1],
                                  self.out_nonlin)
        space = Conv2DSpace(shape=dataset.X_topo_space.shape,
                            num_channels=1,
                            axes=['c', 0, 1, 'b'])
        model = MLP(batch_size=model_params['batch_size'],
                    layers=layers,
                    input_space=space)
        return model


class SigmoidTrainer(MLPTrainer):
    def get_cost_fn(self):
        if self.model_params.get('dropout'):
            return Dropout()
        return None


class RectifiedLinearTrainer(MLPTrainer):
    def get_cost_fn(self):
        if self.model_params.get('dropout'):
            return Dropout()
        return None


class AutoEncoderTrainer(BaseTrainer):
    def __init__(self, runner, model_params, resume=False,
                 resume_data=None, s3_data=None, **kwargs):
        dataset = create_dense_design_matrix(x=runner.dp.train_set_x)

        if resume:
            model, model_params = self.resume_model(model_params, resume_data)
        else:
            model = self.new_model(model_params, dataset=dataset)

        termination_criterion = MaxEpochNumber(model_params['maxnum_iter'])
        algorithm = SGD(learning_rate=model_params['learning_rate']['init'],
                        monitoring_dataset=dataset,
                        cost=MeanSquaredReconstructionError(),
                        termination_criterion=termination_criterion,
                        batch_size=model_params['batch_size'])
        ext = AutoEncoderStatReporter(runner, resume=resume,
                                      resume_data=resume_data,
                                      save_freq=model_params['save_freq'])
        self.train_obj = Train(dataset=dataset,
                               model=model,
                               algorithm=algorithm,
                               extensions=[ext])

    def train(self):
        self.train_obj.main_loop()

    def resume_model(self, model_params, resume_data):
        model = resume_data['model']
        #TODO: FIX IT
        model = pylearn2.monitor.push_monitor(model, 'monitor_validation', True)
        return model, model_params

    def new_model(self, model_params, dataset):
        corruptor = BinomialCorruptor(corruption_level=model_params['noise_level'])
        model = DenoisingAutoencoder(nvis=dataset.X.shape[1],
                                     nhid=model_params['hidden_outputs'],
                                     irange=model_params['irange'],
                                     corruptor=corruptor,
                                     act_enc='tanh',
                                     act_dec=None)
        return model
