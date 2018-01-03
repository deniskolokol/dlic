import json
import pytest
from django.core.urlresolvers import reverse
from rest_framework import status
from job.models import LearnModel, TrainEnsemble
from job.model_settings import SPEARMINT
from data_management.models import DataSet


pytestmark = pytest.mark.django_db(transaction=True)


def test_model_create_only_key(client):
    data = {}
    response = client.post(reverse('model-list'), data, format='json')
    rdata = response.content
    gdata = json.dumps({'detail': 'Authentication credentials were not '
                                  'provided.'})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert rdata == gdata


def test_model_create_invalid_ensemble(ensemble_mrnn, client):
    user = ensemble_mrnn.user
    apikey = user.apikey.key
    data = {'ensemble': 4354353}
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = response.content
    gdata = json.dumps({
        'model_params': ['This field is required.'],
        'ensemble': ["Invalid pk '4354353' - object does not exist."],
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert rdata == gdata


def test_model_invalid_model_params(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {"a": 5, "b": 2, 'maxnum_iter': 37, 'random_sparse': True}
    data = {
        'key': apikey,
        'ensemble': ensemble.id,
        'model_name': 'CONV',
        'model_params': params,
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = response.content
    gdata = json.dumps({'invalid model parameters': ['a', 'b']})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert len(json.loads(response.content).keys()) == 1
    assert len(json.loads(response.content)['invalid model parameters']) == 2
    assert rdata == gdata


def test_model_invalid_model_parameters_type(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='CONV').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {'img_size': 4, 'maxnum_iter': 56, 'random_sparse': True}
    data = {
        'ensemble': ensemble.id,
        'model_name': 'CONV',
        'model_params': params
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = response.content
    gdata = json.dumps({'img_size': ["Ensure this value is greater than or "
                                     "equal to 8."]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert len(json.loads(response.content).keys()) == 1
    assert rdata == gdata


def test_model_invalid_model_name(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MRNN').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    data = {
        'ensemble': ensemble.id,
        'model_name': 'CONre',
        'model_params': {'img_size': 4}
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = response.content
    gdata = json.dumps({
        "model_name": ["Select a valid choice. CONre is not one of the "
                       "available choices."]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert len(json.loads(response.content).keys()) == 1
    assert rdata == gdata


def test_model_add_to_empty_ensemble(client, trained_mlp_ensemble, get_url):
    apikey = trained_mlp_ensemble.user.apikey.key
    for lm in trained_mlp_ensemble.learn_models.all():
        response = client.delete(get_url("model-detail", kwargs={'pk': lm.id},
                                         params=[('key', apikey)]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
    data = {
        'ensemble': trained_mlp_ensemble.pk,
        'model_params': {'maxnum_iter': 456},
        'model_name': 'AUTOENCODER',
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    del rdata['created']
    del rdata['updated']
    del rdata['id']
    data['model_params']['save_freq'] = 25
    data.update({'name': None, u'state': u'NEW', u'training_time': 0.0})
    assert data == rdata


def test_model_invalid_create_no_ensemble(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MRNN').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    data = {
        'model_params': {'T': 54, 'maxnum_iter': 45},
        'model_name': "MRNN"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        "ensemble": ["This field is required."]
    }


def test_model_valid_create_model_no_model_name(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MRNN').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    data = {
        'ensemble': ensemble.id,
        'model_params': {'T': 54, 'maxnum_iter': 45},
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = json.loads(response.content)
    gdata = {
        "id": rdata['id'], "ensemble": ensemble.id, "model_name": "MRNN",
        "model_params": {"maxnum_iter": 45, "T": 54},
        'state': u'NEW', 'training_time': 0.0, 'name': None}
    assert response.status_code == status.HTTP_201_CREATED
    del rdata['created']
    del rdata['updated']
    assert gdata == rdata


def test_model_valid_create_model_model_name(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_RECTIFIED').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    params = {
        'maxnum_iter': 453, 'dropout': True,
        'layers': [{
            'irange': 0.005, 'dim': 3,
            'type': 'rectified_linear', 'layer_name': 'h0'
        }]
    }
    data = {
        'ensemble': ensemble.id,
        'model_params': params,
        'model_name': 'MLP_RECTIFIED',
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    rdata.pop('updated')
    params.update({'save_freq': 25, 'learning_rate': {'constant': False},
                   'momentum': {'constant': False}})
    gdata = {"id": rdata['id'], "ensemble": ensemble.id, "model_name":
             "MLP_RECTIFIED", "model_params": params, 'state': 'NEW',
             'training_time': 0, 'name': None}
    assert gdata == rdata
    assert gdata == rdata
    assert rdata['model_params'] == data['model_params']


def test_model_valid_create_mlp_rectified(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_RECTIFIED').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    data = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "save_freq": 30,
            "percent_batches_per_iter": 100,
            "dropout": False,
            "learning_rate": {
                "constant": False
            },
            "momentum": {
                'init': 1,
                "constant": False
            },
            "layers": [
                {
                    "layer_name": "h0",
                    "sparse_init": 40,
                    "dim": 100,
                    'type': 'rectified_linear',
                },
                {
                    "layer_name": "h1",
                    "sparse_init": 23,
                    "dim": 200,
                    'type': 'rectified_linear',
                }
            ]
        },
        "model_name": "MLP_RECTIFIED",
        "name": "my cool name",
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    rdata = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    model_id = rdata.pop('id')
    del rdata['created']
    del rdata['updated']
    del rdata['state']
    del rdata['training_time']
    assert data['model_params'] == rdata['model_params']
    assert response.status_code == status.HTTP_201_CREATED
    assert rdata['ensemble'] == ensemble.id
    assert rdata['model_name'] == 'MLP_RECTIFIED'
    assert rdata['name'] == 'my cool name'
    mparams = LearnModel.objects.get(id=model_id).model_params
    assert rdata['model_params'] == mparams


def test_model_valid_create_mlp_rectified2(ensemble_all_types, client):
    ensemble = LearnModel.objects.get(model_name='MLP_RECTIFIED').ensemble
    user = ensemble.user
    apikey = user.apikey.key
    data = {
        "ensemble": ensemble.id,
        "model_params": {
            "batch_size": 128,
            "maxnum_iter": 100,
            "save_freq": 30,
            "percent_batches_per_iter": 100,
            "dropout": False,
            "learning_rate": {
                "constant": False
            },
            "momentum": {
                'init': 2,
                "constant": False,
                'start': 4,
                'stop': 2
            },
            "layers": [
                {
                    "layer_name": "h0",
                    "sparse_init": 40,
                    "dim": 100,
                    'type': 'rectified_linear',
                },
                {
                    "layer_name": "h1",
                    "sparse_init": 23,
                    "dim": 200,
                    'type': 'rectified_linear',
                }
            ]
        },
        "model_name": "MLP_RECTIFIED"
    }
    response = client.post(reverse('model-list') + '?key=' +
                           apikey, data, format='json')
    m = json.loads(response.content)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert m["momentum"] == ["Momentum start value >= stop value."]


@pytest.mark.xfail
def test_model_valid_create_model_different_model_names(ensemble_all_types,
                                                        client):
    ensembles = ensemble_all_types
    user = ensembles[0].user
    apikey = user.apikey.key
    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']
    type = {'MLP_SIGMOID': 'sigmoid', 'MLP_RECTIFIED': 'rectified_linear',
            'MLP_MAXOUT': 'maxout', 'MLP_MAXOUT_CONV': 'maxout_convolution'}
    for y in zip(models, ensembles):
        x = y[0]
        ensemble = y[1]
        if x == 'MRNN':
            params = {'T': 12, 'maxnum_iter': 67}
        elif x in ['CONV']:
            params = {'maxnum_iter': 453, 'img_size': 8}
        elif x == 'AUTOENCODER':
            params = {'maxnum_iter': 456}

        elif x == 'MLP_MAXOUT':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45,
                    'num_units': 56, 'layer_name': 'h0',
                    'type': type[x], 'max_col_norm': 34,
                }]
            }
        elif x == 'MLP_MAXOUT_CONV':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45, 'num_units': 56,
                    'layer_name': 'h0', 'type': type[x],
                    'max_kernel_norm': 34, "pool_stride": 45,
                    "pad": 45, "kernel_shape": 34,
                    "pool_shape": 89
                }]
            }
        else:
            params = {
                'maxnum_iter': 453, 'dropout': True,
                'layers': [{
                    'irange': 0.005, 'dim': 45,
                    'layer_name': 'h0', 'type': type[x]
                }]
            }
        data = {
            'ensemble': ensemble.id,
            'model_params': params,
            'model_name': x,
        }
        response = client.post(reverse('model-list') +
                               '?key=' + apikey, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        rdata = json.loads(response.content)
        model_id = rdata.pop('id')
        del rdata['created']
        del rdata['updated']
        assert params == rdata['model_params']
        assert rdata['ensemble'] == ensemble.id
        assert rdata['model_name'] == x
        mparams = LearnModel.objects.get(id=model_id).model_params
        assert rdata['model_params'] == mparams


def test_model_update_all_types(client, ensemble_all_types, get_url):
    ensembles = ensemble_all_types
    user = ensembles[0].user
    apikey = user.apikey.key
    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']
    type = {'MLP_SIGMOID': 'sigmoid', 'MLP_RECTIFIED': 'rectified_linear',
            'MLP_MAXOUT': 'maxout', 'MLP_MAXOUT_CONV': 'maxout_convolution'}
    for y in zip(models, ensembles):
        x = y[0]
        ensemble = y[1]
        if x == 'MRNN':
            params = {'T': 12, 'maxnum_iter': 67}
        elif x in ['CONV']:
            params = {'maxnum_iter': 453, 'img_size': 8, 'random_sparse': True}
        elif x == 'AUTOENCODER':
            params = {'maxnum_iter': 456}
        elif x == 'MLP_MAXOUT':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45, 'num_units': 56,
                    'layer_name': 'h0', 'type': type[x],
                    'max_col_norm': 34
                }]
            }
        elif x == 'MLP_MAXOUT_CONV':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45, 'num_units': 56,
                    'layer_name': 'h0', 'type': type[x],
                    'max_kernel_norm': 34, "pool_stride": 45,
                    "pad": 45, "kernel_shape": 34,
                    "pool_shape": 89
                }]
            }
        else:
            params = {
                'maxnum_iter': 453, 'dropout': True,
                'layers': [{
                    'irange': 0.005, 'dim': 45,
                    'layer_name': 'h0', 'type': type[x]
                }]
            }
        data = {
            'model_params': params,
            'model_name': x,
        }
        model = LearnModel.objects.get(ensemble=ensemble)
        response = client.patch(get_url("model-detail",
                                kwargs={'pk': model.id},
                                params=[('key', apikey)]),
                                data=data,
                                format='json')
        rdata = json.loads(response.content)
        gdata = {"id": 2, "ensemble": ensemble.id, "model_name": x,
                 "model_params": params}
        assert response.status_code == status.HTTP_200_OK
        assert LearnModel.objects.get(ensemble=ensemble).model_params == \
            rdata['model_params']
        assert rdata['ensemble'] == gdata['ensemble']
        assert rdata['model_name'] == gdata['model_name']
        assert len(rdata) == 9


def test_model_update_all_types_read_only_fields(client, ensemble_all_types,
                                                 get_url):
    ensembles = ensemble_all_types
    user = ensembles[0].user
    apikey = user.apikey.key
    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']
    type = {'MLP_SIGMOID': 'sigmoid', 'MLP_RECTIFIED': 'rectified_linear',
            'MLP_MAXOUT': 'maxout', 'MLP_MAXOUT_CONV': 'maxout_convolution'}
    for y in zip(models, ensembles):
        x = y[0]
        ensemble = y[1]
        if x == 'MRNN':
            params = {'T': 12, 'maxnum_iter': 67}
        elif x in ['CONV']:
            params = {'maxnum_iter': 453, 'img_size': 8,
                      'dropout': 0.5, 'random_sparse': False}
        elif x == 'AUTOENCODER':
            params = {'maxnum_iter': 456}
        elif x == 'MLP_MAXOUT':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45, 'num_units': 56,
                    'layer_name': 'h0', 'type': type[x],
                    'max_col_norm': 34
                }]
            }
        elif x == 'MLP_MAXOUT_CONV':
            params = {
                'maxnum_iter': 453,
                'layers': [{
                    'irange': 0.005, 'num_pieces': 45, 'num_units': 56,
                    'layer_name': 'h0', 'type': type[x],
                    'max_kernel_norm': 34, "pool_stride": 45,
                    "pad": 45, "kernel_shape": 34,
                    "pool_shape": 89
                }]
            }

        else:
            params = {
                'maxnum_iter': 453, 'dropout': True,
                'layers': [{
                    'irange': 0.005, 'dim': 45,
                    'layer_name': 'h0', 'type': type[x]
                }]
            }

        data = {
            'model_params': params,
            'model_name': x,
            'state': 'DELETE',
        }
        model = LearnModel.objects.get(ensemble=ensemble)
        response = client.patch(get_url("model-detail",
                                kwargs={'pk': model.id},
                                params=[('key', apikey)]),
                                data=data,
                                format='json')
        rdata = json.loads(response.content)
        gdata = {"id": 2, "ensemble": ensemble.id, "model_name": x,
                 "model_params": params}
        assert response.status_code == status.HTTP_200_OK
        assert LearnModel.objects.get(ensemble=ensemble).model_params == \
            rdata['model_params']
        assert rdata['ensemble'] == gdata['ensemble']
        assert rdata['model_name'] == gdata['model_name']
        assert len(rdata) == 9
        assert rdata['state'] != 'DELETE'


def test_model_delete(client, ensemble_all_types, get_url):
    ensembles = ensemble_all_types
    user = ensembles[0].user
    apikey = user.apikey.key
    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']
    for y in zip(models, ensembles):
        ensemble = y[1]
        model = LearnModel.objects.get(ensemble=ensemble)
        assert model.state != 'DELETED'
        response = client.delete(get_url("model-detail",
                                 kwargs={'pk': model.id},
                                 params=[('key', apikey)]),
                                 format='json')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert LearnModel.objects.get(ensemble=ensemble).state == 'DELETED'


def test_model_get(client, ensemble_all_types, get_url):
    ensembles = ensemble_all_types
    user = ensembles[0].user
    apikey = user.apikey.key
    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']
    for y in zip(models, ensembles):
        x = y[0]
        ensemble = y[1]
        model = LearnModel.objects.get(ensemble=ensemble)
        response = client.get(get_url("model-detail",
                                      kwargs={'pk': model.id},
                                      params=[('key', apikey)]),
                              format='json')
        rdata = json.loads(response.content)
        gdata = {"id": model.id, "ensemble": ensemble.id, "model_name": x,
                 "model_params": model.model_params}
        assert response.status_code == status.HTTP_200_OK
        assert LearnModel.objects.get(ensemble=ensemble).model_params == \
            rdata['model_params']
        assert rdata['ensemble'] == gdata['ensemble']
        assert rdata['model_name'] == gdata['model_name']
        assert len(rdata) == 9


def test_ensemble_config(client, get_url, data_set_ts):
    user = data_set_ts.data.user
    dset1 = data_set_ts
    dset2 = DataSet.objects.create(data=data_set_ts.data, filters=[],
                                   name='test.csv.zip', key='key',
                                   user=data_set_ts.user)
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ensemble_id = json.loads(response.content)['id']
    data = {
        'ensemble': ensemble_id,
        'model_params': {'maxnum_iter': 10},
        'model_name': 'MRNN',
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert TrainEnsemble.objects.get(pk=ensemble_id).config == SPEARMINT


def test_ensemble_config_list(client, get_url, data_set_ts):
    user = data_set_ts.data.user
    dset1 = data_set_ts
    dset2 = DataSet.objects.create(data=data_set_ts.data, filters=[],
                                   name='test.csv.zip', key='key',
                                   user=data_set_ts.user)
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ensemble_id = json.loads(response.content)['id']
    data = [
        {
            'ensemble': ensemble_id,
            'model_params': {'maxnum_iter': 10},
            'model_name': 'MRNN',
        }, {
            'ensemble': ensemble_id,
            'model_params': {'maxnum_iter': 10},
            'model_name': 'MRNN',
        }
    ]
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert TrainEnsemble.objects.get(pk=ensemble_id).config == SPEARMINT
    assert TrainEnsemble.objects.get(pk=ensemble_id).learn_models.count() == 2


def test_model_list_for_ensemble(client, user, trained_mlp_ensemble,
                                 ensemble_mlp_sigmoid):
    apikey = trained_mlp_ensemble.user.apikey.key
    response = client.get(reverse('model-list') + '?key=' + apikey,
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    assert trained_mlp_ensemble.learn_models.live().count() == \
        len(json.loads(response.content))


def test_model_list_shared(client, user, trained_mlp_ensemble,
                           ensemble_mlp_sigmoid):
    apikey = ensemble_mlp_sigmoid.user.apikey.key
    assert trained_mlp_ensemble.share()
    response = client.get(reverse('model-list') + '?key=' + apikey,
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    assert len(json.loads(response.content)) == 3


def test_model_restart(client, trained_mlp_ensemble, patch_queue):
    apikey = trained_mlp_ensemble.user.apikey.key
    lm1 = trained_mlp_ensemble.learn_models.all()[0]
    response = client.post(reverse('model-restart', kwargs={'pk': lm1.pk})
                           + '?key=' + apikey, format='json')
    assert response.status_code == status.HTTP_200_OK
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    assert lm1.state == 'QUEUE'
    #TODO: assert queue message in patch_queue


def test_model_resume_with_iter(client, trained_mlp_ensemble):
    apikey = trained_mlp_ensemble.user.apikey.key
    lm1 = trained_mlp_ensemble.learn_models.all()[0]
    data = {'iteration': 10}
    response = client.post(reverse('model-resume', kwargs={'pk': lm1.pk})
                           + '?key=' + apikey,
                           data=data, format='json')
    assert response.status_code == status.HTTP_200_OK
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    assert lm1.state == 'QUEUE'


def test_model_resume_without_iter(client, trained_mlp_ensemble):
    apikey = trained_mlp_ensemble.user.apikey.key
    lm1 = trained_mlp_ensemble.learn_models.all()[0]
    response = client.post(reverse('model-resume', kwargs={'pk': lm1.pk})
                           + '?key=' + apikey, format='json')
    assert response.status_code == status.HTTP_200_OK
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    assert lm1.state == 'QUEUE'


def test_model_set_name(client, trained_mlp_ensemble, get_url):
    apikey = trained_mlp_ensemble.user.apikey.key
    lm1 = trained_mlp_ensemble.learn_models.all()[0]
    assert lm1.name is None
    data = {'name': 'my new model'}
    response = client.patch(get_url("model-detail", kwargs={'pk': lm1.id},
                                    params=[('key', apikey)]),
                            data=data)
    assert response.status_code == status.HTTP_200_OK
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    assert lm1.name == 'my new model'
