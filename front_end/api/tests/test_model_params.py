import json
import pytest
from django.core.urlresolvers import reverse
from rest_framework import status
from job.models import LearnModel


pytestmark = pytest.mark.django_db


def test_valid_mlp_sigmoid(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_SIGMOID').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.pk,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "dropout": True,
            "learning_rate": {},
            "momentum": {},
            "layers": [{
                "type": "sigmoid",
                "dim": 200,
                "sparse_init": 10,
                "layer_name": "h0"
            }, {
                "type": "sigmoid",
                "dim": 200,
                "irange": 0.005,
                "layer_name": "h1"
            }]
        },
        "model_name": "MLP_SIGMOID",
        "name": "my cool name",
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    del m['created']
    del m['updated']
    del m['id']
    params['model_params'].update({'save_freq': 25})
    params['model_params']['learning_rate']['constant'] = False
    params['model_params']['momentum']['constant'] = False
    params.update({'state': "NEW", 'training_time': 0})
    assert params == m


def test_valid_mlp_maxout_conv(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT_CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "save_freq": 25,
            "batch_size": 128,
            "learning_rate": {
                "constant": False
            },
            "momentum": {
                "constant": False
            },
            "layers": [
                {
                    "max_kernel_norm": 0.9,
                    "num_pieces": 2,
                    "pool_stride": 2,
                    "pad": 0,
                    "num_units": 48,
                    "layer_name": "h0",
                    "type": "maxout_convolution",
                    "pool_shape": 4,
                    "kernel_shape": 8,
                    "irange": 0.0005
                },
                {
                    "max_kernel_norm": 1.9365,
                    "num_pieces": 2,
                    "pool_stride": 2,
                    "pad": 3,
                    "num_units": 48,
                    "layer_name": "h1",
                    "type": "maxout_convolution",
                    "pool_shape": 4,
                    "kernel_shape": 8,
                    "irange": 0.0005
                },
                {
                    "max_kernel_norm": 1.9365,
                    "num_pieces": 4,
                    "pool_stride": 2,
                    "pad": 3,
                    "num_units": 24,
                    "layer_name": "h2",
                    "type": "maxout_convolution",
                    "pool_shape": 2,
                    "kernel_shape": 5,
                    "irange": 0.0005
                }
            ]
        },
        "model_name": "MLP_MAXOUT_CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    del m['created']
    del m['updated']
    del m['id']
    params['name'] = None
    params['model_params'].update({'save_freq': 25})
    params['model_params']['learning_rate']['constant'] = False
    params['model_params']['momentum']['constant'] = False
    params.update({'state': "NEW", 'training_time': 0})
    assert params == m


def test_invalid_mlp_maxout_conv(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT_CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "save_freq": 25,
            "batch_size": 128,
            "learning_rate": {
                "constant": False
            },
            "momentum": {
                "constant": False
            },
            "layers": [
                {
                    "max_kernel_norm": 0.9,
                    "num_pieces": 2,
                    "pool_stride": 2,
                    "pad": 0,
                    "num_units": 48,
                    "layer_name": "h0",
                    "type": "maxout_convolution",
                    "pool_shape": 4,
                    "kernel_shape": 8,
                    "irange": 0.0005,
                    "sparse_init": None,
                }
            ]
        },
        "model_name": "MLP_MAXOUT_CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        u'layers': [u'Specify only one parameter: sparse_init or irange.']
    }


def test_valid_mlp_maxout(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h1"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    del m['created']
    del m['updated']
    del m['id']
    params['name'] = None
    params['model_params'].update({'save_freq': 25})
    params['model_params']['learning_rate']['constant'] = False
    params['model_params']['momentum']['constant'] = False
    params.update({'state': "NEW", 'training_time': 0})
    assert params == m


def test_valid_mrnn(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MRNN').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
        },
        "model_name": "MRNN"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    m = json.loads(response.content)
    del m['created']
    del m['updated']
    del m['id']
    params.update({'state': "NEW", 'training_time': 0, 'name': None})
    assert params == m


def test_invalid_mrnn(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MRNN').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {},
        "model_name": "MRNN"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    #TODO: should show error about missed maxnum_iter not about model_params
    # because we are providing empty model_params
    assert json.loads(response.content) == {
        "model_params": ["This field is required."]
    }


def test_valid_conv(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 128,
            "dropout": 0.5,
            "random_sparse": True,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    m = json.loads(response.content)
    del m['created']
    del m['updated']
    del m['id']
    params.update({'state': "NEW", 'training_time': 0, 'name': None})
    params['model_params']['test_freq'] = 10
    params['model_params']['save_freq'] = 20
    params['model_params']['random_sparse'] = True
    assert params == m


def test_invalid_conv_rsparse_required(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 128,
            "dropout": 0.5,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    m = json.loads(response.content)
    assert m == {u'random_sparse': [u'This field is required.']}


def test_valid_conv2(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 128,
            "dropout": True,
            "random_sparse": False,
            "learning_rate": {
                "init": 0.1,
            },
            "momentum": {
                "init": 0.5,
            }
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    m = json.loads(response.content)
    del m['created']
    del m['updated']
    del m['id']
    params.update({'state': "NEW", 'training_time': 0, 'name': None})
    params['model_params']['test_freq'] = 10
    params['model_params']['save_freq'] = 20
    assert params == m


def test_valid_conv_no_dropout(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 128,
            "random_sparse": False,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_201_CREATED


def test_invalid_conv_img_size(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 65,
            "dropout": 0,
            "random_sparse": False,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    m = json.loads(response.content)
    assert m == {u'img_size': [u'Image size must be a multiple of 8.']}


def test_invalid_conv_img_size_to_big(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 136,
            "random_sparse": False,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'img_size': ['Ensure this value is less than or equal to 128.']
    }


def test_invalid_conv_invalid_dropout(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "maxnum_iter": 30,
            "img_size": 64,
            "dropout": 'asd',
            "random_sparse": False,
        },
        "model_name": "CONV"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {"dropout": ["Enter a number."]}


def test_valid_mlp_maxout2(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {
                "init": 0.1,
                "final": 0.001
            },
            "momentum": {
                "init": 0.5,
                "constant": True
            },
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                }
            ]
        },
        "model_name": "MLP_MAXOUT",
        "name": "best model"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    del m['created']
    del m['updated']
    del m['id']
    params['model_params'].update({'save_freq': 25})
    params['model_params']['learning_rate']['constant'] = False
    params.update({'state': "NEW", 'training_time': 0})
    assert params == m


def test_valid_mlp_maxout3(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {
                "constant": True
            },
            "momentum": {
                "init": 0.5,
                "constant": True
            },
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h1"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "max_col_norm": 1.9365,
                    "sparse_init": 10,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    m = json.loads(response.content)
    del m['created']
    del m['updated']
    del m['id']
    params['name'] = None
    params['model_params'].update({'save_freq': 25})
    params.update({'state': "NEW", 'training_time': 0})
    assert params == m


def test_valid_mlp_maxout4(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "save_freq": 30,
            "learning_rate": {
                "constant": True
            },
            "momentum": {
                "init": 0.5,
                "constant": True,
                "final": 0.75
            },
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h1"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "max_col_norm": 1.9365,
                    "sparse_init": 10,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    m = json.loads(response.content)
    del m['created']
    del m['updated']
    del m['id']
    params.update({'state': "NEW", 'training_time': 0, 'name': None})
    assert params == m


def test_invalid_mlp_maxout_dropout(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            'dropout': True,
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h1"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert m['invalid model parameters'] == [u'dropout']


def test_invalid_mlp_maxout_layers_missing(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": []
        },
        "model_name": "MLP_MAXOUT"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert m['layers'] == [u'This field is required.']


def test_invalid_mlp_maxout_irange_and_sparse_init(ensemble_all_types, client):

    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key

    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "sparse_init": 10,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }

    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    m = json.loads(response.content)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert m['layers'] == [
        u'Specify only one parameter: sparse_init or irange.'
    ]


def test_invalid_mlp_maxout_invalid_lr(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": 4,
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_mlp_maxout_invalid_momentum(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": 3,
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_mlp_maxout__layer_miss_maxcolnorm(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": "240",
                    "num_pieces": "2",
                    "irange": 0.005,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h1"
                },
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_mlp_maxout_extra_param(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "learning_rate_init": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_mlp_maxout_extra_param_in_layer(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "max_kernel_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_mlp_maxout_different_layers(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h0"
                },
                {
                    "type": "maxout_convolutional",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_valid_mlp_maxout_invalid_types_string(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": '128',
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_valid_mlp_maxout_invalid_types_blank(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": '',
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_valid_mlp_maxout_invalid_types_layer(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": '2',
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_valid_mlp_maxout_invalid_percent_batches(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 101,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "type": "maxout",
                    "num_units": 240,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "max_col_norm": 1.9365,
                    "layer_name": "h2"
                }
            ]
        },
        "model_name": "MLP_MAXOUT"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = {
        "percent_batches_per_iter": [
            "Ensure this value is less than or equal to 100."
        ]
    }
    assert json.loads(response.content) == error


def test_valid_rectified_update(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_RECTIFIED').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 700,
            "maxnum_iter": 50,
            "percent_batches_per_iter": 100,
            "dropout": True,
            "learning_rate": {},
            "momentum": {},
            "layers": [
                {
                    "dim": 200,
                    "sparse_init": 10,
                    "type": "rectified_linear",
                    "layer_name": "h0"
                },
                {
                    "dim": 200,
                    "sparse_init": 10,
                    "type": "rectified_linear",
                    "layer_name": "h1"
                }
            ]
        },
        "model_name": "MLP_RECTIFIED"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, params, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    model_id = json.loads(response.content)['id']
    params = {
        "model_params": {
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "dropout": False,
            "batch_size": 128,
            "learning_rate": {
                "decay_factor": 1.00004,
                "init": 0.1,
                "constant": False,
                "final": 0.01
            },
            "momentum": {
                "constant": False,
                "stop": 20,
                "final": 0.95,
                "start": 1
            },
            "layers": [
                {
                    "dim": 200,
                    "sparse_init": 10,
                    "type": "rectified_linear",
                    "layer_name": "h0"
                },
                {
                    "dim": 200,
                    "sparse_init": 10,
                    "type": "rectified_linear",
                    "layer_name": "h1"
                }
            ]
        }
    }
    response = client.patch(reverse('model-detail',
                                    kwargs={'pk': model_id}) + '?key=' +
                            apikey, params, format='json')

    assert response.status_code == status.HTTP_200_OK
    data = LearnModel.objects.get(pk=model_id).model_params
    assert data == params['model_params']
    params = {
        "model_params": {
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "dropout": False,
            "batch_size": 128,
            "learning_rate": {
            },
            "momentum": {
            },
            "layers": [
                {
                    "dim": 200,
                    "sparse_init": 10,
                    "type": "rectified_linear",
                    "layer_name": "h0"
                }
            ]
        }
    }
    response = client.patch(reverse('model-detail',
                                    kwargs={'pk': model_id}) + '?key=' +
                            apikey, params, format='json')
    assert response.status_code == status.HTTP_200_OK
    data = LearnModel.objects.get(pk=model_id).model_params
    data['learning_rate']['constant'] = False
    data['momentum']['constant'] = False
    params['model_params']['momentum'] = data['momentum']
    params['model_params']['learning_rate'] = data['learning_rate']
    assert data == params['model_params']


def test_valid_mlp_maxout5(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_MAXOUT_CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        "ensemble": ensemble.pk,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "learning_rate": {
                "init": 0.05,
                "final": 0.000001,
                "decay_factor": 1.00004
            },
            "momentum": {
                "init": 0.5,
                "final": 0.7,
                "start": 1,
                "stop": 250
            },
            "layers": [
                {
                    "type": "maxout_convolution",
                    "num_units": 48,
                    "num_pieces": 2,
                    "irange": 0.005,
                    "pad": 0,
                    "kernel_shape": 8,
                    "pool_shape": 4,
                    "pool_stride": 2,
                    "max_kernel_norm": 0.9,
                    "layer_name": "h0"
                }
            ]
        },
        "model_name": "MLP_MAXOUT_CONV"
    }
    response = client.post(reverse('model-list') + '?key=' + apikey,
                           params, format='json')
    assert response.status_code == status.HTTP_201_CREATED
