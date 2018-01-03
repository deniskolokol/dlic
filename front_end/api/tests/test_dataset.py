import json
import pytest
from data_management.models import DataSet
from job.models import TrainEnsemble
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_dataset_list(data_set, client, get_url):
    user = data_set.data.user
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    rdata = json.loads(response.content)
    assert DataSet.objects.filter(user=user).count() == len(rdata)


def test_dataset_create(client, get_url, data_file_csv):
    user = data_file_csv.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'last_column_is_output': True,
        'name': 'test_name.csv',
        'filters': [
            {'name': 'shuffle'},
            {'name': 'normalize'}
        ],
        'shared': False,
        'data': 1,
        'id': 1
    }
    assert rdata == data


def test_dataset_create_no_last_column(client, get_url, data_file_csv):
    user = data_file_csv.user
    data_file_csv.meta['last_column_info']['classes'] = None
    data_file_csv.save()
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv.pk,
        'last_column_is_output': False,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'last_column_is_output': False,
        'name': 'test_name.csv',
        'filters': [
            {'name': 'shuffle'},
            {'name': 'normalize'}
        ],
        'shared': False,
        'data': 1,
        'id': 1
    }
    assert rdata == data


def test_dataset_create_last_column_missed(client, get_url, data_file_csv):
    user = data_file_csv.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv.pk,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    assert rdata == {u'last_column_is_output': [u'This field is required.']}


def test_dataset_create_invalid_last_output(client, get_url, data_file_csv):
    user = data_file_csv.user
    data_file_csv.meta['last_column_info']['classes'] = None
    data_file_csv.save()
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    assert rdata == {
        'last_column_is_output': [
            'Last column should contains only integers, started from 0'
        ]
    }


def test_dataset_create_invalid_user(client, get_url, data_file, user):
    data = {
        'name': 'test_name.csv',
        'data': data_file.pk,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_dataset_create_invalid_state(client, get_url, data_file):
    user = data_file.user
    data_file.state -= 1
    data_file.save()
    data = {
        'name': 'test_name.csv',
        'data': data_file.pk,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        "data": ["Invalid pk '1' - object does not exist."]
    }


def test_dataset_create_shared_data(client, get_url, data_file, user):
    data = {
        'name': 'test_name.csv',
        'data': data_file.pk,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"}
        ]
    }
    data_file.shared = True
    data_file.save()
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED


def test_dataset_create_no_filters(client, get_url, data_file):
    user = data_file.user
    data = {
        'name': 'test_name.csv',
        'data': data_file.pk
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'name': 'test_name.csv',
        'filters': [],
        'shared': False,
        'last_column_is_output': None,
        'data': 1,
        'id': 1
    }
    assert rdata == data


def test_dataset_get(data_set, client, get_url):
    user = data_set.data.user
    response = client.get(get_url('dataset-detail',
                                  kwargs={'pk': data_set.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'name': 'test.csv.zip',
        'filters': [
            {'name': 'shuffle'},
        ],
        'last_column_is_output': None,
        'shared': False,
        'data': 1,
        'id': 1
    }
    assert rdata == data


def test_dataset_delete(data_set, client, get_url):
    user = data_set.data.user
    response = client.delete(get_url('dataset-detail',
                                     kwargs={'pk': data_set.pk},
                                     params=[('key', user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert DataSet.objects.get(pk=data_set.pk).state == DataSet.ST_DELETE


def test_delete_dataset_with_ensemble(ensemble, client, get_url):

    user = ensemble.user
    dataset = ensemble.train_dataset
    response = client.delete(get_url('dataset-detail',
                                     kwargs={'pk': dataset.pk},
                                     params=[('key', user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert DataSet.objects.get(pk=dataset.pk).state == DataSet.ST_READY
    assert json.loads(response.content) == {
        'detail': 'This dataset has ensembles, delete not allowed.'
    }


def test_delete_dataset_with_deleted_ensemble(ensemble, client, get_url):
    user = ensemble.user
    dataset = ensemble.train_dataset
    ensemble.to_delete_state()
    response = client.delete(get_url('dataset-detail',
                                     kwargs={'pk': dataset.pk},
                                     params=[('key', user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert DataSet.objects.get(pk=dataset.pk).state == DataSet.ST_DELETE


def test_dataset_list_filter_for_ensemble(data_set_csv, client,
                                          get_url, data_file_csv):
    user = data_set_csv.user
    df = data_set_csv.data
    data_set_csv2 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           last_column_is_output=True,
                                           name='test.csv.zip',
                                           key='/s3key')
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv2.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_id = json.loads(response.content)['id']
    data_file_csv.meta['num_columns'] = 10
    data_file_csv.user = df.user
    data_file_csv.save()
    data_set_csv3 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           last_column_is_output=True,
                                           name='test1.csv.zip',
                                           key='/s3keya')
    DataSet.objects.create(data=data_file_csv,
                           filters=data_set_csv.filters,
                           user=user,
                           name='test2.csv.zip',
                           key='/s3keyb')
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key),
                                          ('for_ensemble', ens_id)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert set([x['id'] for x in rdata]) == {data_set_csv.pk,
                                             data_set_csv2.pk,
                                             data_set_csv3.pk}


def test_dataset_list_filter_for_ensemble_eq_input(data_set_csv, client,
                                                   get_url, data_file_csv):
    user = data_set_csv.user
    df = data_set_csv.data
    data_set_csv2 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           last_column_is_output=True,
                                           name='test.csv.zip',
                                           key='/s3key')
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv2.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_id = json.loads(response.content)['id']
    data_file_csv.meta['num_columns'] = 3
    data_file_csv.user = df.user
    data_file_csv.save()
    data_set_csv3 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           last_column_is_output=True,
                                           name='test1.csv.zip',
                                           key='/s3keya')
    data_set_csv4 = DataSet.objects.create(data=data_file_csv,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           last_column_is_output=False,
                                           name='test2.csv.zip',
                                           key='/s3keyb')
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key),
                                          ('for_ensemble', ens_id),
                                          ('equal_input', '1')]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert set([x['id'] for x in rdata]) == {data_set_csv.pk,
                                             data_set_csv2.pk,
                                             data_set_csv3.pk,
                                             data_set_csv4.pk}


def test_dataset_list_filter_for_ensemble_no_datasets(data_set_csv, client,
                                                      get_url, data_file_csv):
    user = data_set_csv.user
    df = data_set_csv.data
    data_set_csv2 = DataSet.objects.create(data=df,
                                           filters=data_set_csv.filters,
                                           user=user,
                                           name='test.csv.zip',
                                           key='/s3key')
    data = {
        'train_dataset': data_set_csv.pk,
        'test_dataset': data_set_csv2.pk,
    }
    response = client.post(get_url('ensemble-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    ens_id = json.loads(response.content)['id']
    data_file_csv.meta['num_columns'] = 10
    data_file_csv.user = df.user
    data_file_csv.save()
    DataSet.objects.create(data=df,
                           filters=data_set_csv.filters,
                           user=user,
                           name='test1.csv.zip',
                           key='/s3keya')
    DataSet.objects.create(data=data_file_csv,
                           filters=data_set_csv.filters,
                           user=user,
                           name='test2.csv.zip',
                           key='/s3keyb')
    ens = TrainEnsemble.objects.get(pk=ens_id)
    ens.train_dataset = None
    ens.test_dataset = None
    ens.save()
    response = client.get(get_url('dataset-list',
                                  params=[('key', user.apikey.key),
                                          ('for_ensemble', ens_id)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert DataSet.objects.all().count() == len(rdata)


def test_dataset_create_output_not_valid_columns(client, get_url,
                                                 data_file_csv_columns):
    user = data_file_csv_columns.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv_columns.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [0, 15, 26]}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    assert rdata == {'non_field_errors': ["This columns doesn't exist: "
                                          "[15, 26]"]}


def test_dataset_create_output_columns_ignored_in_output(client, get_url,
                                                         data_file_csv):
    user = data_file_csv.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"},
            {"name": "ignore", 'columns': [5, 6]},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [0, 5, 6]}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    assert rdata == {'non_field_errors': ["You can't select an ignored "
                                          "columns([5, 6]) in output columns "
                                          "filter"]}


def test_dataset_create_output_columns_different_types(client, get_url,
                                                       data_file_csv_columns):
    user = data_file_csv_columns.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv_columns.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [0, 1, 3]}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)

    assert rdata == {'non_field_errors': ["You can't select different "
                                          "types({0: u'f', 1: u'i', 3: u'S'}) "
                                          "of "
                                          "columns in output columns filter"]}


def test_dataset_create_output_columns_valid(client, get_url,
                                             data_file_csv_columns):
    user = data_file_csv_columns.user
    data = {
        'name': 'test_name.csv',
        'data': data_file_csv_columns.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [0, 2]}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'last_column_is_output': True,
        'name': 'test_name.csv',
        'filters': [
            {'name': 'shuffle'},
            {'name': 'normalize'},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [0, 2]}

        ],
        'shared': False,
        'data': 1,
        'id': 1
    }
    assert rdata == data

    data = {
        'name': 'test_name.csv',
        'data': data_file_csv_columns.pk,
        'last_column_is_output': True,
        'filters': [
            {"name": "shuffle"},
            {"name": "normalize"},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [1, 3]}
        ]
    }
    response = client.post(get_url('dataset-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    rdata.pop('created')
    data = {
        'last_column_is_output': True,
        'name': 'test_name.csv',
        'filters': [
            {'name': 'shuffle'},
            {'name': 'normalize'},
            {"name": "ignore", 'columns': []},
            {"name": "permute", "columns": []},
            {"name": "outputs", "columns": [1, 3]}

        ],
        'shared': False,
        'data': 1,
        'id': 2
    }
    assert rdata == data