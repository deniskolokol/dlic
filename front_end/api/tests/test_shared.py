import json
import pytest
from rest_framework import status
from job.models import TrainEnsemble
from data_management.models import DataSet, DataFile


pytestmark = pytest.mark.django_db


def test_private_data_file(data_file, user, get_url, client):
    response = client.get(get_url('data-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 0
    response = client.get(get_url('data-detail',
                                  kwargs={'pk': data_file.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get(get_url('data-list',
                                  params=[('key', data_file.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('data-detail',
                                  kwargs={'pk': data_file.pk},
                                  params=[('key', data_file.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_shared_data_file(data_file, user, get_url, client):
    data_file.share()
    assert DataFile.objects.get(pk=data_file.pk).shared
    response = client.get(get_url('data-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('data-detail',
                                  kwargs={'pk': data_file.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK

    response = client.get(get_url('data-list',
                                  params=[('key', data_file.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('data-detail',
                                  kwargs={'pk': data_file.pk},
                                  params=[('key', data_file.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_shared_data_file_update(data_file, user, get_url, client):
    data_file.share()
    data = {'id': data_file.pk, 'name': 'new_name_for_test.ts'}
    key = data_file.user.apikey.key
    response = client.put(get_url('data-detail',
                                  kwargs={'pk': data_file.pk},
                                  params=[('key', key)]),
                          data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert json.loads(response.content) == {
        "detail": {"status": "fail", "problem": "Permission denied"}
    }


def test_private_data_set(data_set, user, get_url, client):
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 0
    response = client.get(get_url('dataset-detail',
                                  kwargs={'pk': data_set.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get(get_url('dataset-list',
                                  params=[('key', data_set.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('dataset-detail',
                                  kwargs={'pk': data_set.pk},
                                  params=[('key', data_set.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_shared_data_set(data_set, user, get_url, client):
    data_set.share()
    assert DataSet.objects.get(pk=data_set.pk).shared
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('dataset-detail',
                                  kwargs={'pk': data_set.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK

    response = client.get(get_url('dataset-list',
                                  params=[('key', data_set.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('dataset-detail',
                                  kwargs={'pk': data_set.pk},
                                  params=[('key', data_set.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK

    # related DataFile also available for another user
    response = client.get(get_url('data-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1


def test_shared_data_file_datasets(data_set, user, get_url, client):
    data_set.share()
    DataSet.objects.create(data=data_set.data, filters=[],
                           user=data_set.user,
                           name='My csv', key='datasets/' + data_set.key)
    response = client.get(get_url('data-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    assert len(rdata[0]['datasets']) == 1
    assert rdata[0]['datasets'][0]['id'] == data_set.pk

    response = client.get(get_url('data-list',
                                  params=[('key', data_set.user.apikey.key)]),
                          format='json')
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    assert len(rdata[0]['datasets']) == 2


def test_private_ensemble(ensemble, user, get_url, client):
    response = client.get(get_url('ensemble-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 0
    response = client.get(get_url('ensemble-detail',
                                  kwargs={'pk': ensemble.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get(get_url('ensemble-list',
                                  params=[('key', ensemble.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('ensemble-detail',
                                  kwargs={'pk': ensemble.pk},
                                  params=[('key', ensemble.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_shared_ensemble(trained_mlp_ensemble, user, get_url, client):
    ensemble = trained_mlp_ensemble
    ensemble.share()
    assert TrainEnsemble.objects.get(pk=ensemble.pk).shared
    response = client.get(get_url('ensemble-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('ensemble-detail',
                                  kwargs={'pk': ensemble.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK

    response = client.get(get_url('ensemble-list',
                                  params=[('key', ensemble.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert len(rdata) == 1
    response = client.get(get_url('ensemble-detail',
                                  kwargs={'pk': ensemble.pk},
                                  params=[('key', ensemble.user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_shared_ensemble_update(trained_mlp_ensemble, user, get_url, client):
    ensemble = trained_mlp_ensemble
    ensemble.share()
    dset = DataSet.objects.create(data=ensemble.train_dataset.data, filters=[],
                                  user=ensemble.user,
                                  name='My csv', key='datasets/test')
    data = {
        'test_dataset': dset.pk,
    }
    response = client.patch(get_url('ensemble-detail',
                                    kwargs={'pk': ensemble.pk},
                                    params=[('key', user.apikey.key)]),
                            data=data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_readonly_models(trained_mlp_ensemble, user, get_url, client):
    ensemble = trained_mlp_ensemble
    ensemble.share()
    lm1, lm2 = ensemble.learn_models.all()
    assert lm1.readonly
    assert lm2.readonly
    assert all(s.readonly for s in lm1.stats.all())
    assert all(s.readonly for s in lm2.stats.all())


def test_shared_data_file_create_dataset(data_file, user, get_url, client):
    data_file.share()
    data = [
        {
            'name': 'test_name.csv',
            'data': data_file.pk,
            'last_column_is_output': True,
            'filters': [
                {"name": "shuffle"},
                {"name": "normalize"}
            ]
        }, {
            'name': 'test_name2.csv',
            'data': data_file.pk,
            'last_column_is_output': True,
            'filters': [
                {"name": "shuffle"},
                {"name": "normalize"}
            ]
        }
    ]
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED


def test_shared_data_file_create_ensemble(data_file, user, get_url, client):
    data_file.share()
    data = [
        {
            'name': 'test_name.csv',
            'data': data_file.pk,
            'last_column_is_output': True,
            'filters': [
                {"name": "shuffle"},
                {"name": "normalize"}
            ]
        }, {
            'name': 'test_name2.csv',
            'data': data_file.pk,
            'last_column_is_output': True,
            'filters': [
                {"name": "shuffle"},
                {"name": "normalize"}
            ]
        }
    ]
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    data = {
        'train_dataset': rdata[0]['id'],
        'test_dataset': rdata[1]['id']
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
