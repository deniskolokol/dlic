import json
import random
import datetime
from dateutil import parser, tz
import pytest
from job.models import TrainEnsemble
from data_management.models import DataSet, DataFile
from rest_framework import status


pytestmark = pytest.mark.django_db(transaction=True)

NET_TYPE = {'TIMESERIES': 'RNN', 'GENERAL': 'DEEPNET', 'IMAGES': 'DEEPNET'}


@pytest.fixture
def prepare_datasets(get_data_set_ts, get_data_set_csv,
                     get_data_set_images):
    f = random.choice((get_data_set_ts, get_data_set_csv, get_data_set_images))
    ds1 = f()
    ds2 = f()
    user = ds1.user
    ds2.user = user
    ds2.save()
    data = ds2.data
    data.user = user
    data.save()
    return ds1, ds2, user


def test_ensemble_create_superuser(client, get_url, prepare_datasets):
    dset1, dset2, user = prepare_datasets
    user.is_superuser = True
    user.save()
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        "id": 1,
        "shared": False,
        "data_type": dset1.data.file_format,
        "send_email_on_change": False,
        "train_dataset": dset1.pk,
        "test_dataset": dset2.pk,
        "state": "empty",
        "models_count": 0,
        "total_time": 0.,
        'test_dataset_name': dset2.name,
        'train_dataset_name': dset1.name,
        'traceback': None,
        'net_type': NET_TYPE[dset1.data.file_format],
    }
    assert rdata == data
    assert TrainEnsemble.objects.all().count() == 1


def test_ensemble_create(client, get_url, prepare_datasets):
    dset1, dset2, user = prepare_datasets
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        "id": 1,
        "shared": False,
        "data_type": dset1.data.file_format,
        "send_email_on_change": False,
        "train_dataset": dset1.pk,
        "test_dataset": dset2.pk,
        "state": "empty",
        "models_count": 0,
        "total_time": 0.,
        'test_dataset_name': dset2.name,
        'train_dataset_name': dset1.name,
        'net_type': NET_TYPE[dset1.data.file_format],
    }
    assert rdata == data
    assert TrainEnsemble.objects.all().count() == 1


def test_ensemble_create_invalid_test_data_user(client, get_url,
                                                prepare_datasets, user):
    dset1, dset2, dset_user = prepare_datasets
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    dset2.user = user
    dset2.save()
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_ensemble_create_invalid_train_data_user(client, get_url,
                                                 prepare_datasets, user):
    dset1, dset2, dset_user = prepare_datasets
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {
        "test_dataset": ["Invalid pk '2' - object does not exist."],
        "train_dataset": ["Invalid pk '1' - object does not exist."]
    }
    assert json.loads(response.content) == data


def test_ensemble_delete(client, get_url, ensemble_mrnn):
    user = ensemble_mrnn.user
    url = get_url('ensemble-detail',
                  kwargs={'pk': ensemble_mrnn.pk},
                  params=[('key', user.apikey.key)])
    response = client.delete(url, format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert TrainEnsemble.objects.all().count() == 1
    assert TrainEnsemble.objects.get(pk=ensemble_mrnn.pk).deleted


def test_ensemble_detail(client, user, get_url, ensemble_mrnn):
    user = ensemble_mrnn.user
    data = {
        'ensemble': ensemble_mrnn.id,
        'model_params': {'h': 8, 'maxnum_iter': 45},
        'model_name': 'MRNN',
    }
    data = [data] * 9
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    response = client.get(get_url('ensemble-detail',
                                  kwargs={'pk': ensemble_mrnn.pk},
                                  params=[('key', user.apikey.key)]))
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    rcreated = parser.parse(rdata.pop('created'))
    now = datetime.datetime.utcnow().replace(tzinfo=tz.tzutc())
    assert now - datetime.timedelta(10) < rcreated
    assert now > rcreated
    data = {
        u'total_time': 0.0,
        u'data_type': u'TIMESERIES',
        u'send_email_on_change': False,
        u'state': u'new',
        u'shared': False,
        u'train_dataset': 1,
        u'id': 1,
        u'models_count': 10,
        u'test_dataset': 2,
        u'test_dataset_name': u'My File',
        u'train_dataset_name': u'test.csv.zip',
        u'net_type': 'RNN',
    }
    assert rdata == data


def test_ensemble_list_filter_by_dataset(client, get_url,
                                         ensemble, data_file_ts):
    user = ensemble.user
    TrainEnsemble.objects.create(
        user=ensemble.user,
        train_dataset=ensemble.train_dataset,
        data_type=TrainEnsemble.TIMESERIES
    )
    df = data_file_ts
    df.user = ensemble.user
    df.save()
    dataset = DataSet.objects.create(data=df, user=df.user,
                                     name='test.csv.zip')
    TrainEnsemble.objects.create(
        user=dataset.data.user,
        train_dataset=dataset,
        data_type=TrainEnsemble.TIMESERIES
    )
    params = [('key', user.apikey.key), ('dataset', ensemble.train_dataset_id)]
    response = client.get(get_url('ensemble-list', params=params),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    assert len(json.loads(response.content)) == 2
    params = [('key', user.apikey.key), ('data', df.pk)]
    response = client.get(get_url('ensemble-list', params=params),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    assert len(json.loads(response.content)) == 1
    params = [('key', user.apikey.key)]
    response = client.get(get_url('ensemble-list', params=params),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    assert len(json.loads(response.content)) == 3


def test_ensemble_create_empty(client, get_url, prepare_datasets):
    dset1, dset2, user = prepare_datasets
    data = {
        'train_dataset': dset1.pk,
        'test_dataset': dset2.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_pk = json.loads(response.content)['id']
    ensemble = TrainEnsemble.objects.get(pk=ens_pk)
    assert ensemble.state == 'EMPTY'
    assert ensemble.data_type == dset1.data.file_format


def test_ensemble_create_without_datasets(client, get_url, user):
    data = {}
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        "train_dataset": ["This field is required."]
    }


def test_ensemble_create_autoencoder(client, get_url, data_set_csv):
    user = data_set_csv.data.user
    data = {
        'train_dataset': data_set_csv.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    assert rdata['net_type'] == TrainEnsemble.NET_AUTOENCODER
    data = {
        'ensemble': rdata['id'],
        'model_params': {
            'maxnum_iter': 45,
            'batch_size': 128
        },
        'model_name': 'AUTOENCODER',
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED


def test_ensemble_create_one_ts_dataset(client, get_url, data_set_ts):
    user = data_set_ts.data.user
    data = {
        'train_dataset': data_set_ts.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        "test_dataset": ["This field is required."]
    }


def test_ensemble_create_mlp_sigmoid(client, get_url, data_set_csv):
    user = data_set_csv.data.user
    data = {
        'train_dataset': data_set_csv.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    assert rdata['net_type'] == TrainEnsemble.NET_AUTOENCODER
    data = {
        'ensemble': rdata['id'],
        'model_name': 'MLP_SIGMOID',
        'model_params': {
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
                },
                {
                    'type': 'sigmoid',
                    'layer_name': 'h1',
                    'dim': 200,
                    'sparse_init': 10,
                },
            ]
        }
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_ensemble_create_model_data_type(client, get_url, data_set_ts):
    user = data_set_ts.data.user
    data = {
        'train_dataset': data_set_ts.pk,
        'test_dataset': data_set_ts.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    assert rdata['net_type'] == TrainEnsemble.NET_RNN
    data = {
        'ensemble': rdata['id'],
        'model_params': {'maxnum_iter': 45},
        'model_name': 'CONV',
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    # only ensemble with data_type = 'IMAGES' should accept CONV models
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {"model_name": ["Ensemble and model use different type of data"]}
    assert json.loads(response.content) == data


def test_ensemble_create_with_different_datasets(client, get_url, data_set_ts,
                                                 data_set_csv):
    user = data_set_ts.data.user
    data_set_csv.user = user
    data_set_csv.save()
    data = {
        'train_dataset': data_set_ts.pk,
        'test_dataset': data_set_csv.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    # different data in same ensemble
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {
        "test_dataset": ["Test and train dataset should be of the same type"]
    }
    assert json.loads(response.content) == data


def test_ensemble_update_with_different_datasets(client, get_url, data_set_ts,
                                                 data_set_csv):
    user = data_set_ts.data.user
    data = {
        'train_dataset': data_set_ts.pk,
        'test_dataset': data_set_ts.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_pk = json.loads(response.content)['id']
    assert TrainEnsemble.objects.get(pk=ens_pk).data_type == 'TIMESERIES'
    data_set_csv.user = user
    data_set_csv.save()
    data = {
        'test_dataset': data_set_csv.pk,
    }
    response = client.patch(get_url('ensemble-detail',
                                    kwargs={'pk': ens_pk},
                                    params=[('key', user.apikey.key)]),
                            data=data, format='json')

    #train and test dataset have different file_format
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {
        "test_dataset": ["Test and train dataset should be of the same type"]
    }
    assert json.loads(response.content) == data


def test_ensemble_create_model_data_type2(client, get_url, data_set_csv):
    user = data_set_csv.data.user
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_pk = json.loads(response.content)['id']
    data = {
        'ensemble': ens_pk,
        'model_params': {'maxnum_iter': 45},
        'model_name': 'CONV',
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    # only ensemble with data_type = 'IMAGES' should accept CONV models
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {"model_name": ["Ensemble and model use different type of data"]}
    assert json.loads(response.content) == data


def test_ensemble_create_model_data_type3(client, get_url, data_set_csv):
    user = data_set_csv.data.user
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv.pk
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_pk = json.loads(response.content)['id']
    data = {
        'ensemble': ens_pk,
        'model_params': {'maxnum_iter': 45},
        'model_name': 'MRNN',
    }
    response = client.post(get_url('model-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    # only ensemble with data_type = 'Timeseries' should accept MRNN models
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {"model_name": ["Ensemble and model use different type of data"]}
    assert json.loads(response.content) == data


def test_ensemble_update(client, get_url, ensemble_mrnn):
    ensemble = ensemble_mrnn
    user = ensemble.user
    assert not TrainEnsemble.objects.get(id=ensemble.id).send_email_on_change
    data = {
        "send_email_on_change": True,
    }
    response = client.patch(get_url("ensemble-detail",
                                    kwargs={'pk': ensemble.id},
                                    params=[('key', user.apikey.key)]),
                            data=data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert TrainEnsemble.objects.get(id=ensemble.id).send_email_on_change


def test_ensemble_delete_with_models(client, get_url, ensemble_mrnn):

    ensemble = ensemble_mrnn
    user = ensemble.user

    response = client.delete(get_url("ensemble-detail",
                             kwargs={'pk': ensemble.id},
                             params=[('key', user.apikey.key)]),
                             format='json')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert TrainEnsemble.objects.get(id=ensemble.id).deleted is True


def test_ensemble_update_with_models(client, get_url, ensemble_mrnn,
                                     data_set_ts):
    ensemble = ensemble_mrnn
    user = ensemble.user
    data_set_ts.user = user
    data_set_ts.save()
    data = {
        "send_email_on_change": True,
        "test_dataset": data_set_ts.id
    }
    response = client.patch(get_url("ensemble-detail",
                                    kwargs={'pk': ensemble.id},
                                    params=[('key', user.apikey.key)]),
                            data=data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert TrainEnsemble.objects.get(id=ensemble.id).send_email_on_change
    assert TrainEnsemble.objects.get(id=ensemble.id).test_dataset.id == \
        data_set_ts.id


def test_ensemble_update_invalid_data(client, get_url, ensemble_mrnn,
                                      data_set_ts):
    ensemble = ensemble_mrnn
    user = ensemble.user
    data = {
        "send_email_on_change": False,
        "test_dataset": 'j'
    }
    response = client.patch(get_url("ensemble-detail",
                                    kwargs={'pk': ensemble.id},
                                    params=[('key', user.apikey.key)]),
                            data=data,
                            format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = {
        "test_dataset": [
            "Incorrect type.  Expected pk value, received unicode."
        ]
    }
    assert json.loads(response.content) == data


def test_is_datasets_valid_resume(client, get_url, ensemble_mrnn):
    ensemble_mrnn.test_dataset = None
    ensemble_mrnn.save()
    key = ensemble_mrnn.user.apikey.key
    response = client.post(get_url('ensemble-resume',
                                   kwargs={'pk': ensemble_mrnn.pk},
                                   params=[('key', key)]))
    assert response.status_code == 400
    assert json.loads(response.content) == {
        "detail": "Ensemble datasets are not configured."
    }


def test_is_datasets_valid_resume_autoencoder(client, get_url,
                                              ensemble_autoencoder):
    ensemble = ensemble_autoencoder
    ensemble.test_dataset = None
    ensemble.save()
    response = client.post(get_url('ensemble-resume',
                                   kwargs={'pk': ensemble.pk},
                                   params=[('key', ensemble.user.apikey.key)]))
    assert response.status_code == 200


def test_ensemble_create_deleted_data_file(client, get_url, data_set_csv):
    user = data_set_csv.user
    df = data_set_csv.data
    data_set_csv2 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           name='test.csv.zip',
                                           key='/s3key')
    response = client.delete(get_url('data-detail',
                                     kwargs={'pk': df.pk},
                                     params=[('key', df.user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert DataFile.objects.get(pk=df.pk).state == DataFile.STATE_DELETING
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv2.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    ens_id = rdata['id']
    assert rdata['train_dataset'] == data_set_csv.pk
    data = {
        'test_dataset': data_set_csv.pk,
        'train_dataset': data_set_csv2.pk,
    }
    response = client.put(get_url('ensemble-detail', kwargs={'pk': ens_id},
                                  params=[('key', user.apikey.key)]),
                          data=data, format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert rdata['test_dataset'] == data_set_csv.pk
