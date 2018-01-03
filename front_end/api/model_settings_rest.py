import validictory
from copy import deepcopy
from django import forms
from api.fields import JSONFormField


CONV = {u'maxnum_iter': 500,
        u'img_size': 32,
        u'layer_params': (u'[conv1]\nepsw=0.001\nepsb=0.002\nmomw=0.9\n'
                          u'momb=0.9\nwc=0.004\nnepsw=0.001\n[conv2]\n'
                          u'epsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\n'
                          u'wc=0.004\n[conv3]\nepsw=0.001\nepsb=0.002\n'
                          u'momw=0.9\nmomb=0.9\nwc=0.004\n[fc10]\nepsw=0.001\n'
                          u'epsb=0.002\nmomw=0.9\nmomb=0.9\nwc=1\n'
                          u'[logprob]\ncoeff=1\n[rnorm1]\nscale=0.00005\n'
                          u'pow=.75\n[rnorm2]\nscale=0.00005\npow=.75'),
        u'layers': (u'[data]\ntype=data\ndataidx=0\n[labels]\ntype=data\n'
                    u'dataidx=1\n[conv1]\ntype=conv\ninputs=data\n'
                    u'channels=3\nfilters=32\npadding=2\nstride=1\n'
                    u'filtersize=5\ninitw=0.0001\npartialsum=4\n'
                    u'sharedbiases=1\n[pool1]\ntype=pool\npool=max\n'
                    u'inputs=conv1\nstart=0\nsizex=3\nstride=2\n'
                    u'outputsx=0\nchannels=32\nneuron=relu\n[rnorm1]\n'
                    u'type=rnorm\ninputs=pool1\nchannels=32\nsize=3\n'
                    u'[conv2]\ntype=conv\ninputs=rnorm1\nfilters=32\n'
                    u'padding=2\nstride=1\nfiltersize=5\nchannels=32\n'
                    u'neuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n'
                    u'[pool2]\ntype=pool\npool=avg\ninputs=conv2\nstart=0\n'
                    u'sizex=3\nstride=2\noutputsx=0\nchannels=32\n'
                    u'[rnorm2]\ntype=rnorm\ninputs=pool2\nchannels=32\nsize=3\n'
                    u'[conv3]\ntype=conv\ninputs=rnorm2\nfilters=64\n'
                    u'padding=2\nstride=1\nfiltersize=5\nchannels=32\n'
                    u'neuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n'
                    u'[pool3]\ntype=pool\npool=avg\ninputs=conv3\nstart=0\n'
                    u'sizex=3\nstride=2\noutputsx=0\nchannels=64\n'
                    u'[fc10]\ntype=fc\noutputs=10\ninputs=pool3\n'
                    u'initw=0.01\n[probs]\ntype=softmax\ninputs=fc10\n'
                    u'[logprob]\ntype=cost.logreg\ninputs=labels,probs'),
        u'dropout': True,
        u'learning_rate': {u'init': 0.001},
        u'momentum': {u'init': 0.05},
        u'random_sparse': False,
        u'test_freq': 10,
        u'save_freq': 50
}

MRNN = {u'T': 20,
 u'cg_max_cg': 40,
 u'cg_min_cg': 1,
 u'f': 2,
 u'h': 2,
 u'lambda': 0.01,
 u'maxnum_iter': 20,
 u'mu': 0.001}



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
    u'hidden_outputs': 20,
    u'noise_level': 0.2,
    u'irange': 0.05,
    u'save_freq': 20,
    u'learning_rate': {u'init': 0.001}
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
    u'out_nonlin': 'SOFTMAX',
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'save_freq': 50,
    u'dropout': False,
    u'momentum': {
        u'init': 0.5,
        u'final': 0.95,
        u'start': 1,
        u'stop': 20,
        u'constant': False
    },
    u'learning_rate': {
        u'init': 0.1,
        u'final': 0.01,
        u'decay_factor': 1.00004,
        u'constant': False
    },
    u'layers': [
        {
            'type': 'sigmoid',
            'layer_name': 'h0',
            'dim': 200,
            'irange': None,
            'sparse_init': 10,
        },
        {
            'type': 'sigmoid',
            'layer_name': 'h1',
            'dim': 200,
            'irange': None,
            'sparse_init': 10,
        },
    ]
}

RECTIFIED = {
    u'batch_size': 128,
    u'out_nonlin': 'SOFTMAX',
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'save_freq': 50,
    u'dropout': False,
    u'momentum': {
        u'init': 0.5,
        u'final': 0.95,
        u'start': 1,
        u'stop': 20,
        u'constant': False
    },
    u'learning_rate': {
        u'init': 0.1,
        u'final': 0.01,
        u'decay_factor': 1.00004,
        u'constant': False
    },
    u'layers': [
        {
            'type': 'rectified_linear',
            'layer_name': None,
            'dim': None,
            'irange': None,
            'sparse_init': None,        },
        {
            'type': 'rectified_linear',
            'layer_name': 'h0',
            'dim': 200,
            'irange': None,
            'sparse_init': 10,
        },
        {
            'type': 'rectified_linear',
            'layer_name': 'h1',
            'dim': 200,
            'irange': None,
            'sparse_init': 10,
        },
    ]
}

MAXOUT = {
    u'batch_size': 128,
    u'out_nonlin': 'SOFTMAX',
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'save_freq': 50,
    u'momentum': {
        u'init': 0.5,
        u'final': 0.95,
        u'start': 1,
        u'stop': 20,
        u'constant': False
    },
    u'learning_rate': {
        u'init': 0.1,
        u'final': 0.01,
        u'decay_factor': 1.00004,
        u'constant': False
    },
    u'layers': [
        {
            'type': 'maxout',
            'layer_name': 'h0',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': None,
            'max_col_norm': 1.9365,
        },
        {
            'type': 'maxout',
            'layer_name': 'h1',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': None,
            'max_col_norm': 1.9365,
        },
        {
            'type': 'maxout',
            'layer_name': 'h2',
            'num_units': 240,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': None,
            'max_col_norm': 1.9365,
        }
    ]
}

MAXOUT_CONV = {
    u'batch_size': 128,
    u'out_nonlin': 'SOFTMAX',
    u'maxnum_iter': 100,
    u'percent_batches_per_iter': 100,
    u'save_freq': 50,
    u'momentum': {
        u'init': 0.5,
        u'final': 0.7,
        u'start': 1,
        u'stop': 250,
        u'constant': False
    },
    u'learning_rate': {
        u'init': 0.05,
        u'final': 0.000001,
        u'decay_factor': 1.00004,
        u'constant': False
    },
    u'layers': [
        {
            'type': 'maxout_convolution',
            'layer_name': 'h0',
            'num_units': 48,
            'num_pieces': 2,
            'irange': 0.005,
            'sparse_init': None,
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
            'sparse_init': None,
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
            'sparse_init': None,
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
        data = data
        schema = schema
        try:
            validictory.validate(data, schema, disallow_unknown_properties=True)
        except ValueError, e:
            self.model_errors = e
            return False
        return True

    def non_valid_fields(self, data, schema):
        # WTF is this?

        k_data = data.keys()
        k_schema = schema.keys()

        return set(k_data) - set(k_schema)

    def clean_maxnum_iter(self):

        mn_iter = self.cleaned_data['maxnum_iter']

        if not mn_iter:
            #TODO This defeats the purpose of a `required` parameter
            #raise forms.ValidationError('Field can\'t be blank')
            print forms.ValidationError('Field can\'t be blank')

        return mn_iter


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
        if (self.model and 'f' in self.model.model_params and
            f != self.model.model_params['f'] and f is not None):
            ermsg = 'This value can\'t be changed after training start.'
            raise forms.ValidationError(ermsg)
        return f

    def clean_h(self):
        h = self.cleaned_data['h']
        if (self.model and 'h' in self.model.model_params and
            h != self.model.model_params['h'] and h is not None):
            ermsg = 'This value can\'t be changed after training start.'
            raise forms.ValidationError(ermsg)
        return h


class CONVSettingsForm(BaseModelSettings):
    img_size = forms.IntegerField(min_value=8, max_value=128, required=False)
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

    def clean_random_sparse(self):
        rs = self.cleaned_data['random_sparse']
        if 'random_sparse' not in self.data:
            raise forms.ValidationError(u'This field is required.')
        return rs


class AutoencoderSettingsForm(BaseModelSettings):
    hidden_outputs = forms.IntegerField(min_value=1, required=False)
    batch_size = forms.IntegerField(min_value=1, required=False)
    save_freq = forms.IntegerField(min_value=5, max_value=100, required=False)
    learning_rate = JSONFormField(required=False)
    noise_level = forms.FloatField(required=False)

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
        if self.isvalid(lr, schema) is True:
            return lr
        raise forms.ValidationError('Invalid learning rate param.')

class TSNESettingsForm(BaseModelSettings):
    n_components = forms.IntegerField(min_value=2, max_value=3, required=False)
    # possible repeat of maxnum_iter from base class
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
    layers = JSONFormField(required=True)

    def clean_batch_size(self):

        batch_size = self.cleaned_data['batch_size']
        return batch_size

    def clean_learning_rate(self):
        lr = self.cleaned_data['learning_rate']
        if lr is None:
            return lr

        if type(lr) != dict:
            raise forms.ValidationError('Learning rate is a dict field, not {0}'.format(type(lr)))

        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 1e-10, 'required':False},
                'final': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'decay_factor': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'constant': {'type': 'boolean', 'required': False}
            }
        }

        valid = self.isvalid(lr, schema)
        if valid:
            if lr.get('init') < lr.get('final'):
                raise forms.ValidationError('Learning rate value initial value < final value.')

            return lr
        raise forms.ValidationError(self.model_errors)

    def clean_momentum(self):
        momentum = self.cleaned_data['momentum']
        if momentum is None:
            return momentum

        if type(momentum) != dict:
            raise forms.ValidationError('Momentum expects a dict field, not {0}'.format(type(momentum)))


        schema = {
            'type': 'object',
            'properties': {
                'init': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'final': {'type': 'number', 'minimum': 1e-10, 'required': False},
                'start': {'type': 'integer', 'minimum': 1, 'required': False},
                'stop': {'type': 'integer', 'minimum': 2, 'required': False},
                'constant': {'type': 'boolean', 'required': False}
            }
        }
        valid_momentum = self.isvalid(momentum, schema)
        if valid_momentum:
            if momentum.get('start') and momentum.get('stop'):
                if momentum.get('start') >= momentum.get('stop'):
                    raise forms.ValidationError('Momentum start value >= stop value.')

            if momentum.get('init') and momentum.get('final'):
                if momentum.get('init') > momentum.get('final'):
                    raise forms.ValidationError('Learning rate initial value > final value.')
            return momentum

        raise forms.ValidationError(self.model_errors)

    def clean_layers(self):
        layers = self.cleaned_data['layers']
        updated_layers = []
        for update_for_layer in layers:
            layer = update_for_layer
                # print self.layer_scheme
                # self.layer_scheme['properties'].pop('sparse_init')
            if 'sparse_init' in layer and 'irange' in layer:
                raise forms.ValidationError('Specify only one parameter: '
                                            'sparse_init or irange.')

            valid_layer = self.isvalid(layer, self.layer_scheme)
            if not valid_layer:
                raise forms.ValidationError(self.model_errors)

            updated_layers.append(layer)

        if not [x for x in updated_layers if x.get('layer_name')]:
            raise forms.ValidationError('Layer name required')
        if len(set(x['layer_name'] for x in updated_layers if x.get(
            'layer_name'))) != len(updated_layers):
            raise forms.ValidationError("Not unique layer name.")
        return updated_layers


class DropoutSettingsForm(MLPSettingsForm):

    dropout = forms.BooleanField(required=False) # default will be False,
    # not None!!

    def clean_dropout(self):
        dropout = self.cleaned_data['dropout']
        if 'dropout' not in self.data:
            raise forms.ValidationError(u'This field is required.')
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
            'irange': {'type': 'number', 'minimum': 0, 'required': False},
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
            'AUTOENCODER': {'default': AUTOENCODER, 'form': AutoencoderSettingsForm},
            'TSNE': {'default': TSNE, 'form': TSNESettingsForm},
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
