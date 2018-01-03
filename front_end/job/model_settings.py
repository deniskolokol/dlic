import validictory
from copy import deepcopy
from django import forms
from api.fields import JSONFormField


CONV_LAYER_PARAMS_CFG = (
    u'[conv1]\n'
    'epsW=%(learning_rate)s\n'
    'epsB=%(learning_rate)s\n'
    'momW=%(momentum)s\n'
    'momB=%(momentum)s\n'
    'wc=0.004\n'
    'randsparse=%(random_sparse)s\n'
    'dropout=%(dropout)s\n'
    '\n'
    '[conv2]\n'
    'epsW=%(learning_rate)s\n'
    'epsB=%(learning_rate)s\n'
    'momW=%(momentum)s\n'
    'momB=%(momentum)s\n'
    'wc=0.004\n'
    'randsparse=%(random_sparse)s\n'
    'dropout=%(dropout)s\n'
    '\n'
    '[conv3]\n'
    'epsW=%(learning_rate)s\n'
    'epsB=%(learning_rate)s\n'
    'momW=%(momentum)s\n'
    'momB=%(momentum)s\n'
    'wc=0.004\n'
    'randsparse=%(random_sparse)s\n'
    'dropout=%(dropout)s\n'
    '\n'
    '[fc10]\n'
    'epsW=%(learning_rate)s\n'
    'epsB=%(learning_rate)s\n'
    'momW=%(momentum)s\n'
    'momB=%(momentum)s\n'
    'wc=1\n'
    '\n'
    '[logprob]\n'
    'coeff=1\n'
    '\n'
    '[rnorm1]\n'
    'scale=0.00005\n'
    'pow=.75\n'
    '\n'
    '[rnorm2]\n'
    'scale=0.00005\n'
    'pow=.75'
)

CONV_LAYERS_CFG = (
    '[data]\n'
    'type=data\n'
    'dataidx=0\n'
    '\n'
    '[labels]\n'
    'type=data\n'
    'dataidx=1\n'
    '\n'
    '[conv1]\n'
    'type=conv\n'
    'inputs=data\n'
    'channels=3\n'
    'filters=32\n'
    'padding=2\n'
    'stride=1\n'
    'filtersize=5\n'
    'initw=0.0001\n'
    'partialsum=4\n'
    'sharedbiases=1\n'
    '\n'
    '[pool1]\n'
    'type=pool\n'
    'pool=max\n'
    'inputs=conv1\n'
    'start=0\n'
    'sizex=3\n'
    'stride=2\n'
    'outputsx=0\n'
    'channels=32\n'
    'neuron=relu\n'
    '\n'
    '[rnorm1]\n'
    'type=rnorm\n'
    'inputs=pool1\n'
    'channels=32\n'
    'size=3\n'
    '\n'
    '[conv2]\n'
    'type=conv\n'
    'inputs=rnorm1\n'
    'filters=32\n'
    'padding=2\n'
    'stride=1\n'
    'filtersize=5\n'
    'channels=32\n'
    'neuron=relu\n'
    'initw=0.01\n'
    'partialsum=4\n'
    'sharedbiases=1\n'
    '\n'
    '[pool2]\n'
    'type=pool\n'
    'pool=avg\n'
    'inputs=conv2\n'
    'start=0\n'
    'sizex=3\n'
    'stride=2\n'
    'outputsx=0\n'
    'channels=32\n'
    '\n'
    '[rnorm2]\n'
    'type=rnorm\n'
    'inputs=pool2\n'
    'channels=32\n'
    'size=3\n'
    '\n'
    '[conv3]\n'
    'type=conv\n'
    'inputs=rnorm2\n'
    'filters=64\n'
    'padding=2\n'
    'stride=1\n'
    'filtersize=5\n'
    'channels=32\n'
    'neuron=relu\n'
    'initw=0.01\n'
    'partialsum=4\n'
    'sharedbiases=1\n'
    '\n'
    '[pool3]\n'
    'type=pool\n'
    'pool=avg\n'
    'inputs=conv3\n'
    'start=0\n'
    'sizex=3\n'
    'stride=2\n'
    'outputsx=0\n'
    'channels=64\n'
    '\n'
    '[fc10]\n'
    'type=fc\n'
    'outputs=%(outputs)s\n'
    'inputs=pool3\n'
    'initw=0.01\n'
    '\n'
    '[probs]\n'
    'type=softmax\n'
    'inputs=fc10\n'
    '\n'
    '[logprob]\n'
    'type=cost.logreg\n'
    'inputs=labels,probs'
)

CONV = {
    u'maxnum_iter': 100,
    u'img_size': 32,
    u'test_freq': 10,
    u'save_freq': 20,
    u'random_sparse': False,
    u'learning_rate': {},
    u'momentum': {},
}

#{u'T': 20,
 #u'cg_max_cg': 40,
 #u'cg_min_cg': 1,
 #u'f': 2,
 #u'h': 2,
 #u'lambda': 0.01,
 #u'maxnum_iter': 20,
 #u'mu': 0.001}
MRNN = {'maxnum_iter': 20}

SPEARMINT = {
    "maxnum_iter":{"min":20, "max":20},
    "T":{"min":20, "max":85},
    "h":{"min":2, "max":100},
    "f":{"min":2, "max":100},
    "cg_max_cg":{"min":40, "max":200},
    "cg_min_cg":{"min":1, "max":30},
    "lambda":{"min":0.01, "max":1.0},
    "mu":{"min":0.001, "max":0.01}
}

AUTOENCODER = {
    u'batch_size': 128,
    u'maxnum_iter': 100,
    u'learning_rate': {}
}

TSNE = {
    u'n_components': 2,
    u'maxnum_iter': 1000,
    u'perplexity': 30,
    u'early_exaggeration': 4.0,
    u'learning_rate': 1000,
    u'init': 'random'
}

SIGMOID = {
    u'batch_size': 128,
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'dropout': True,
    u'momentum': {
        u'constant': False
    },
    u'learning_rate': {
        u'constant': False
    },
    u'layers': [
        {
            'type': 'sigmoid',
            'layer_name': 'h0',
            'dim': 200,
            'sparse_init': 10,
            'irange': 0.05,
        },
        {
            'type': 'sigmoid',
            'layer_name': 'h1',
            'dim': 200,
            'sparse_init': 10,
            'irange': 0.05,
        },
    ]
}

RECTIFIED = {
    u'batch_size': 128,
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'dropout': True,
    u'momentum': {
        u'constant': False
    },
    u'learning_rate': {
        u'constant': False
    },
    u'layers': [
        {
            'type': 'rectified_linear',
            'layer_name': 'h0',
            'dim': 200,
            'sparse_init': 10,
            'irange': 0.05,
        },
        {
            'type': 'rectified_linear',
            'layer_name': 'h1',
            'dim': 200,
            'sparse_init': 10,
            'irange': 0.05,
        },
    ]
}

MAXOUT = {
    u'batch_size': 128,
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'momentum': {
        u'constant': False
    },
    u'learning_rate': {
        u'constant': False
    },
    u'layers': [
        {
            'type': 'maxout',
            'layer_name': 'h0',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': 10,
            'max_col_norm': 1.9365,
        },
        {
            'type': 'maxout',
            'layer_name': 'h1',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': 10,
            'max_col_norm': 1.9365,
        },
        {
            'type': 'maxout',
            'layer_name': 'h2',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': 10,
            'max_col_norm': 1.9365,
        }
    ]
}

MAXOUT_CONV = {
    u'batch_size': 128,
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'momentum': {
        u'constant': False
    },
    u'learning_rate': {
        u'constant': False
    },
    u'layers': [
        {
            'type': 'maxout_convolution',
            'layer_name': 'h0',
            'num_units': 48,
            'num_pieces': 2,
            'irange': 0.005,
            'pad': 0,
            'kernel_shape': 8,
            'pool_shape': 4,
            'pool_stride': 2,
            'max_kernel_norm': 0.9
        },
        {
            'type': 'maxout_convolution',
            'layer_name': 'h1',
            'num_units': 48,
            'num_pieces': 2,
            'irange': 0.005,
            'pad':3,
            'kernel_shape': 8,
            'pool_shape': 4,
            'pool_stride': 2,
            'max_kernel_norm': 1.9365
        },
        {
            'type': 'maxout_convolution',
            'layer_name': 'h2',
            'num_units': 24,
            'num_pieces': 4,
            'irange': 0.005,
            'pad':3,
            'kernel_shape': 5,
            'pool_shape': 2,
            'pool_stride': 2,
            'max_kernel_norm': 1.9365
        }
    ]
}

class BaseModelSettings(forms.Form):
    maxnum_iter = forms.IntegerField(min_value=1, required=False)

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        self.is_user_update = kwargs.pop('user_update', True)
        super(BaseModelSettings, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(BaseModelSettings, self).clean()
        for k, v in cleaned_data.items():
            if v is None:
                del cleaned_data[k]
        return cleaned_data

    def isvalid(self, data, schema):
        try:
            validictory.validate(data, schema, disallow_unknown_properties=True)
        except ValueError:
            return False
        return True


class MRNNSettingsForm(BaseModelSettings):
    T = forms.IntegerField(min_value=1, required=False)
    cg_max_cg = forms.IntegerField(min_value=1, required=False)
    cg_min_cg = forms.IntegerField(min_value=1, required=False)
    f = forms.IntegerField(min_value=1, required=False)
    h = forms.IntegerField(min_value=1, required=False)
    mu = forms.FloatField(min_value=0, required=False)
    # lambda is python keyword, so adding it in __init__

    def __init__(self, *args, **kwargs):
        super(MRNNSettingsForm, self).__init__(*args, **kwargs)
        self.fields['lambda'] = forms.FloatField(min_value=0, required=False)

    def clean_T(self):
        return None if self.is_user_update else self.cleaned_data['T']

    def clean_f(self):
        f = self.cleaned_data['f']
        if ('f' in self.model.model_params and
            f != self.model.model_params['f'] and f is not None):
            ermsg = 'This value can\'t be changed after training start.'
            raise forms.ValidationError(ermsg)
        return f

    def clean_h(self):
        h = self.cleaned_data['h']
        if ('h' in self.model.model_params and
            h != self.model.model_params['h'] and h is not None):
            ermsg = 'This value can\'t be changed after training start.'
            raise forms.ValidationError(ermsg)
        return h


class CONVSettingsForm(BaseModelSettings):
    img_size = forms.IntegerField(min_value=8, required=False)
    test_freq = forms.IntegerField(min_value=5, required=False)
    save_freq = forms.IntegerField(min_value=5, max_value=100, required=False)
    dropout = forms.FloatField(min_value=0, max_value=1, required=False)
    random_sparse = forms.BooleanField(required=False)
    learning_rate = JSONFormField(required=False)
    momentum = JSONFormField(required=False)

    def clean_learning_rate(self):
        lr = self.cleaned_data['learning_rate']
        if lr is None:
            return lr
        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 0, 'maximum': 10}
            }
        }
        if self.isvalid(lr, schema) is True:
            return lr
        raise forms.ValidationError('Invalid learning rate parameter.')

    def clean_momentum(self):
        mn = self.cleaned_data['momentum']
        if mn is None:
            return mn
        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 0, 'maximum': 10}
            }
        }
        if self.isvalid(mn, schema) is True:
            return mn
        raise forms.ValidationError('Invalid momentum parameter.')

    def clean_img_size(self):
        img_size = self.cleaned_data['img_size']
        if img_size is not None and img_size % 8 != 0:
            raise forms.ValidationError(u'Image size must be a multiple of 8.')
        return img_size


class AutoencoderSettingsForm(BaseModelSettings):
    hidden_outputs = forms.IntegerField(min_value=1, required=False)
    batch_size = forms.IntegerField(min_value=1, required=False)
    save_freq = forms.IntegerField(min_value=5, max_value=100, required=False)
    learning_rate = JSONFormField(required=False)
    noise_level = forms.FloatField(required=False)
    irange = forms.FloatField(required=False)

    def clean_learning_rate(self):
        lr = self.cleaned_data['learning_rate']
        if lr is None:
            return lr
        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 0}
            }
        }
        if self.isvalid(lr, schema):
            return lr
        raise forms.ValidationError('Invalid learning rate param.')


class TSNESettingsForm(BaseModelSettings):
    n_components = forms.IntegerField(min_value=2, max_value=3, required=False)
    # possibly a repeat of maxnum_iter from base class
    #n_iter = forms.IntegerField(min_value=200, max_value=10000, required=False)
    perplexity = forms.FloatField(min_value=1.0, max_value=100.0, required=False)
    early_exaggeration =  forms.FloatField(min_value=1.0, max_value=100.0, required=False)
    learning_rate = forms.FloatField(min_value=100.0, max_value=1000.0, required=False)
    init = forms.ChoiceField(required=False,
                            choices=[ ('random','random'), ('pca', 'PCA') ])
    tsne_output = forms.CharField(required=False)


class MLPSettingsForm(BaseModelSettings):
    batch_size = forms.IntegerField(min_value=1, required=False)
    percent_batches_per_iter = forms.IntegerField(min_value=1, max_value=100,
                                                  required=False)
    save_freq = forms.IntegerField(min_value=5, max_value=100, required=False)
    learning_rate = JSONFormField(required=False)
    momentum = JSONFormField(required=False)
    layers = JSONFormField(required=False)

    def clean_learning_rate(self):
        lr = self.cleaned_data['learning_rate']
        if lr is None:
            return lr
        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 1e-10},
                'final': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'decay_factor': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'constant': {'type': 'boolean'}
            }
        }
        if self.isvalid(lr, schema):
            if not lr['constant']:
                if not all(x in lr for x in ('decay_factor', 'final')):
                    raise forms.ValidationError('Invalid settings for constant = false.')
                if lr['init'] < lr['final']:
                    raise forms.ValidationError('Learning rate value initial value < final value.')
            return lr
        raise forms.ValidationError('Invalid learning rate parameter.')

    def clean_momentum(self):
        momentum = self.cleaned_data['momentum']
        if momentum is None:
            return momentum
        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 1e-10},
                'final': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'start': {'type': 'integer', 'minimum': 1, 'required': False},
                'stop': {'type': 'integer', 'minimum': 2, 'required': False},
                'constant': {'type': 'boolean'}
            }
        }
        if self.isvalid(momentum, schema):
            if not momentum['constant']:
                if not all(x in momentum for x in ('start', 'stop', 'final')):
                    raise forms.ValidationError('Invalid settings for constant = false.')
                if momentum['start'] >= momentum['stop']:
                    raise forms.ValidationError('Momentum start value >= stop value.')
                if momentum['init'] > momentum['final']:
                    raise forms.ValidationError('Learning rate initial value > final value.')
            return momentum
        raise forms.ValidationError('Invalid momentum parameter.')

    def clean_layers(self):
        layers = self.cleaned_data['layers']
        if layers is None:
            return layers

        updated_layers = []
        for update_for_layer in layers:
            layer = deepcopy(self.default_layer)
            layer.update(update_for_layer)
            if not self.isvalid(layer, self.layer_scheme):
                raise forms.ValidationError("Invalid layer parameter.")
            if ('sparse_init' in update_for_layer and
                update_for_layer.get('irange') is None):
                if not isinstance(layer['sparse_init'], int):
                    raise forms.ValidationError('sparse_init should be an integer.')
            elif ('irange' in update_for_layer and
                  update_for_layer.get('sparse_init') is None):
                if not isinstance(layer['irange'], float):
                    raise forms.ValidationError('irange should be float.')
            elif ('sparse_init' in update_for_layer and
                  'irange' in update_for_layer):
                raise forms.ValidationError('Specify only one parameter: sparse_init or irange.')
            else:
                raise forms.ValidationError('Specify sparse_init or irange.')
            updated_layers.append(layer)
        if len(set(x['layer_name'] for x in updated_layers)) != len(updated_layers):
            raise forms.ValidationError("Not unique layer name.")
        return updated_layers


class DropoutSettingsForm(MLPSettingsForm):

    dropout = forms.BooleanField(required=False) # default will be False, not None!!

    def clean_dropout(self):
        dropout = self.cleaned_data['dropout']
        if 'dropout' not in self.data:
            dropout = None
        if (dropout != self.model.model_params['dropout'] and
            dropout is not None and self.model.state != 'NEW'):
            ermsg = 'This value can be changed only for new models.'
            raise forms.ValidationError(ermsg)
        return dropout


class SigmoidSettingsForm(DropoutSettingsForm):
    layer_scheme = {
        'type': 'object',
        'properties': {
            'type': {'type': 'string', 'pattern': '^sigmoid$'},
            'layer_name': {'type': 'string', 'minLength': 1},
            'dim': {'type': 'integer', 'minimum': 1},
            'irange': {'type': 'any', 'minimum': 0, 'required': False}, # can be None
            'sparse_init': {'type': 'any', 'minimum': 1, 'required': False},
        }
    }
    default_layer = deepcopy(SIGMOID['layers'][0])


class RectifiedLinearSettingsForm(DropoutSettingsForm):
    layer_scheme = {
        'type': 'object',
        'properties': {
            'type': {'type': 'string', 'pattern': '^rectified_linear$'},
            'layer_name': {'type': 'string', 'minLength': 1},
            'dim': {'type': 'integer', 'minimum': 1},
            'irange': {'type': 'any', 'minimum': 0, 'required': False},
            'sparse_init': {'type': 'any', 'minimum': 1, 'required': False},
        }
    }
    default_layer = deepcopy(RECTIFIED['layers'][0])


class MaxoutSettingsForm(MLPSettingsForm):
    layer_scheme = {
        'type': 'object',
        'properties': {
            'type': {'type': 'string', 'pattern': '^maxout$'},
            'layer_name': {'type': 'string', 'minLength': 1},
            'num_units': {'type': 'integer', 'minimum': 1},
            'num_pieces': {'type': 'integer', 'minimum': 1},
            'irange': {'type': 'any', 'minimum': 0, 'required': False},
            'sparse_init': {'type': 'any', 'minimum': 1, 'required': False},
            'max_col_norm': {'type': 'number', 'minimum': 0},
        }
    }
    default_layer = deepcopy(MAXOUT['layers'][0])


class MaxoutConvSettingsForm(MLPSettingsForm):
    layer_scheme = {
        'type': 'object',
        'properties': {
            'type': {'type': 'string', 'pattern': '^maxout_convolution$'},
            'layer_name': {'type': 'string', 'minLength': 1},
            'num_units': {'type': 'integer', 'minimum': 1},
            'num_pieces': {'type': 'integer', 'minimum': 1},
            'irange': {'type': 'any', 'minimum': 0},
            'max_kernel_norm': {'type': 'number', 'minimum': 0},
            "pool_stride": {'type': 'integer', 'minimum': 0},
            "pad": {'type': 'integer', 'minimum': 0},
            "kernel_shape": {'type': 'integer', 'minimum': 0},
            "pool_shape": {'type': 'integer', 'minimum': 0},
        }
    }
    default_layer = deepcopy(MAXOUT_CONV['layers'][0])


SETTINGS = {'MRNN': {'default': MRNN, 'form': MRNNSettingsForm},
            'CONV': {'default': CONV, 'form': CONVSettingsForm},
            'TSNE': {'default': TSNE, 'form': TSNESettingsForm},
            'AUTOENCODER': {'default': AUTOENCODER, 'form': AutoencoderSettingsForm},
            'MLP_SIGMOID': {'default': SIGMOID, 'form': SigmoidSettingsForm},
            'MLP_RECTIFIED': {'default': RECTIFIED, 'form': RectifiedLinearSettingsForm},
            'MLP_MAXOUT': {'default': MAXOUT, 'form': MaxoutSettingsForm},
            'MLP_MAXOUT_CONV': {'default': MAXOUT_CONV, 'form': MaxoutConvSettingsForm},
            'SPEARMINT': {'default': SPEARMINT, 'form': None},
           }

def get_default_settings(model_name):
    return deepcopy(SETTINGS[model_name]['default'])

def get_settings_form(model_name):
    return SETTINGS[model_name]['form']
