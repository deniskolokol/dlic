import json
import pytest
from data_management.models import DataFile
from rest_framework import status


pytestmark = pytest.mark.django_db


def test_data_create_timeseries(client, user, get_url, settings):
    settings.DMWORKER_CALLBACK_URL = 'http://testserver/parsed/'
    key = user.apikey.key
    data = {
        'name': 'my file',
        'file_format': 'TIMESERIES',
        'data': '1,2,3|1,0;2,2,3|0,1\n4,5,6|0,1'
    }
    response = client.post(get_url('data-list', params=[('key', key)]),
                           data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    result = {
        'datasets': [],
        'state': 'Parsing',
        'meta': {},
        'shared': False,
        'file_format': None,
        'name': 'my file'
    }
    del rdata['created']
    assert len(rdata['parse_logs']) == 1
    del rdata['parse_logs']
    assert DataFile.objects.get(pk=rdata['id']).key.endswith('.ts')
    del rdata['id']
    assert rdata == result


def test_data_create_csv(client, user, get_url, settings):
    settings.DMWORKER_CALLBACK_URL = 'http://testserver/parsed/'
    key = user.apikey.key
    data = {
        'name': 'my file',
        'file_format': 'GENERAL',
        'data': 'a,b,c\n1,2,3\n4,5,6'
    }
    response = client.post(get_url('data-list', params=[('key', key)]),
                           data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    result = {
        'datasets': [],
        'state': 'Parsing',
        'meta': {},
        'shared': False,
        'file_format': None,
        'name': 'my file'
    }
    del rdata['created']
    assert len(rdata['parse_logs']) == 1
    del rdata['parse_logs']
    assert DataFile.objects.get(pk=rdata['id']).key.endswith('.csv')
    del rdata['id']
    assert rdata == result


def test_data_create_with_csv_file(client, user, get_url, tmpdir, settings):
    settings.DMWORKER_CALLBACK_URL = 'http://testserver/parsed/'
    key = user.apikey.key
    ufile = tmpdir.join('mnist data.csv')
    ufile.write('a,b,c\n1,2,3\n4,5,6')
    ufile.name = 'mnist data.csv'
    data = {
        'file': ufile
    }
    response = client.post(get_url('data-list', params=[('key', key)]),
                           data, format='multipart')
    rdata = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    result = {
        'datasets': [],
        'state': 'Parsing',
        'meta': {},
        'shared': False,
        'file_format': None,
        'name': 'mnist data.csv'
    }
    del rdata['created']
    assert len(rdata['parse_logs']) == 1
    del rdata['parse_logs']
    assert DataFile.objects.get(pk=rdata['id']).key.endswith('.csv')
    del rdata['id']
    assert rdata == result


def test_data_create_invalid_ext(client, user, get_url, tmpdir, settings):
    key = user.apikey.key
    ufile = tmpdir.join('mnist data.rar')
    ufile.write('a,b,c\n1,2,3\n4,5,6')
    ufile.name = 'mnist data.rar'
    data = {'file': ufile}
    response = client.post(get_url('data-list', params=[('key', key)]),
                           data, format='multipart')
    rdata = json.loads(response.content)
    ext = ', '.join(settings.DATA_FILE_EXT)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert rdata == {
        'file': [
            'Not supported file extension. Supported extensions: %s' % ext
        ]
    }


def test_data_create_with_file(client, user, get_url, tmpdir, settings):
    settings.DMWORKER_CALLBACK_URL = 'http://testserver/parsed/'
    key = user.apikey.key
    ufile = tmpdir.join('mnist data.ts')
    ufile.write('a,b,c\n1,2,3\n4,5,6')
    ufile.name = 'mnist data.csv'
    data = {
        'file': ufile
    }
    response = client.post(get_url('data-list', params=[('key', key)]),
                           data, format='multipart')
    rdata = json.loads(response.content)
    assert response.status_code == status.HTTP_201_CREATED
    result = {
        'datasets': [],
        'state': 'Parsing',
        'meta': {},
        'shared': False,
        'file_format': None,
        'name': 'mnist data.csv'
    }
    del rdata['created']
    assert len(rdata['parse_logs']) == 1
    del rdata['parse_logs']
    del rdata['id']
    assert rdata == result


def test_data_list(client, data_file_list, get_url):
    user = data_file_list[0].user
    df2 = data_file_list[1]
    df2.user = user
    df2.save()
    response = client.get(get_url('data-list',
                                  params=[('key', user.apikey.key)]),
                          format='json')
    rdata = json.loads(response.content)
    assert DataFile.objects.filter(user=user).count() == len(rdata)


def test_data_get(client, ensemble_mrnn, get_url):
    df = ensemble_mrnn.train_dataset.data
    key = ensemble_mrnn.user.apikey.key
    response = client.get(get_url('data-detail',
                                  kwargs={'pk': df.pk},
                                  params=[('key', key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    rdata.pop('created')
    rdata.pop('parse_logs')
    data = {
        "id": 1,
        "shared": False,
        "name": "test.ts",
        "datasets": [{
            'id': 1,
            'name': 'test.csv.zip',
            'last_column_is_output': None,
            'filters': [{"name": "shuffle"}],
        }],
        "meta": {
            u'archive_path': u'manualx.ts',
            u'data_rows': 32,
            u'output_size': 2,
            u'data_type': u'TIMESERIES',
            u'binary_output': True,
            u'binary_input': False,
            u'min_timesteps': 95,
            u'empty_rows': 0,
            u'version': 3,
            u'max_timesteps': 97,
            u'input_size': 2,
            u'classes': {
                u'1': 121,
                u'0': 2951
            },
            u'size': 6002
        },
        "state": "Ready",
        "file_format": "TIMESERIES"
    }

    assert DataFile.objects.get(pk=df.pk).name == data['name']

    rdata_filters = json.loads(rdata['datasets'][0]['filters'])[0]
    data_filters = data['datasets'][0]['filters'][0]
    del rdata['datasets'][0]['filters']
    del data['datasets'][0]['filters']

    assert rdata_filters == data_filters
    assert rdata == data


def test_data_update(client, ensemble_mrnn, get_url):
    df = ensemble_mrnn.train_dataset.data
    data = {'id': df.pk, 'name': 'new_name_for_test.ts'}
    assert df.name != data['name']
    key = ensemble_mrnn.user.apikey.key
    response = client.put(get_url('data-detail',
                                  kwargs={'pk': df.pk},
                                  params=[('key', key)]),
                          data, format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    rdata.pop('created')
    rlogs = rdata.pop('parse_logs')
    data = {
        "id": 1,
        "shared": False,
        "name": "new_name_for_test.ts",
        "datasets": [{
            'id': 1,
            'name': 'test.csv.zip',
            'last_column_is_output': None,
            'filters': [{'name': 'shuffle'}],
        }],
        "meta": {
            u'archive_path': u'manualx.ts',
            u'data_rows': 32,
            u'output_size': 2,
            u'data_type': u'TIMESERIES',
            u'binary_output': True,
            u'binary_input': False,
            u'min_timesteps': 95,
            u'empty_rows': 0,
            u'version': 3,
            u'max_timesteps': 97,
            u'input_size': 2,
            u'classes': {
                u'1': 121,
                u'0': 2951
            },
            u'size': 6002
        },
        "state": "Ready",
        "file_format": "TIMESERIES"
    }
    assert DataFile.objects.get(pk=df.pk).name == data['name']

    rdata_filters = json.loads(rdata['datasets'][0]['filters'])[0]
    data_filters = data['datasets'][0]['filters'][0]
    del rdata['datasets'][0]['filters']
    del data['datasets'][0]['filters']

    assert rdata_filters == data_filters
    assert rdata == data
    assert len(rlogs) == 3


def test_data_delete(client, get_url, data_file):
    df = data_file
    response = client.delete(get_url('data-detail',
                                     kwargs={'pk': df.pk},
                                     params=[('key', df.user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert DataFile.objects.get(pk=df.pk).state == DataFile.STATE_DELETING


def test_data_share_non_admin(client, get_url, data_file):
    df = data_file
    response = client.post(get_url('data-share',
                                   kwargs={'pk': df.pk},
                                   params=[('key', df.user.apikey.key)]),
                           format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not DataFile.objects.get(pk=df.pk).shared


def test_data_share_admin(client, get_url, data_file):
    df = data_file
    user = data_file.user
    user.is_superuser = True
    user.save()
    response = client.post(get_url('data-share',
                                   kwargs={'pk': df.pk},
                                   params=[('key', df.user.apikey.key)]),
                           format='json')
    assert response.status_code == status.HTTP_200_OK
    assert DataFile.objects.get(pk=df.pk).shared