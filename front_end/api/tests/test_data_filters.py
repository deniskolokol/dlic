import json
import pytest
from rest_framework import status
from data_management.models import DataSet

pytestmark = pytest.mark.django_db


def test_filters_merge_same_datafile(client, get_url, data_file_list):
    df = data_file_list[0]
    user = df.user
    data = {
        'name': 'test_name.csv',
        'data': df.pk,
        'filters': [
            {"name": "merge", "datas": [df.pk]}
        ]
    }
    url = get_url('dataset-list', params=[('key', user.apikey.key)])
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    error = {
        'filters': [{
            'merge': {'datas': ['The elements of this field must be unique']}
        }]
    }
    assert rdata == error

    df2 = data_file_list[1]
    df2.user = user
    df2.save()

    data = {
        'name': 'test_name.csv',
        'data': df.pk,
        'filters': [
            {"name": "merge", "datas": [df2.pk, df2.pk]}
        ]
    }
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    assert rdata == error


def test_filters_merge_with_other_user_file(client, get_url, data_file_list):
    df, df2, _ = data_file_list
    user = df.user
    data = {
        'name': 'test_name.csv',
        'data': df.pk,
        'filters': [
            {"name": "merge", "datas": [df2.pk]}
        ]
    }
    url = get_url('dataset-list', params=[('key', user.apikey.key)])
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    data = {'filters': [{'merge': {'datas': ['Elements 2 not found']}}]}
    assert rdata == data


def test_filters_valid(client, get_url, data_file_list):
    df, df2, df3 = data_file_list
    user = df.user
    df2.user = user
    df2.save()
    df3.shared = True
    df3.save()
    data = [
        {
            'name': 'Train dataset',
            'data': df.pk,
            'filters': [
                {"name": "merge", "datas": [df2.pk, df3.pk]},
                {"name": "shuffle"},
                {"name": "normalize"},
                {"name": "split", 'start': 0, 'end': 75}
            ]
        }, {
            "name": "Test dataset",
            'data': df.pk,
            'filters': [
                {"name": "merge", "datas": [df2.pk, df3.pk]},
                {"name": "shuffle"},
                {"name": "normalize"},
                {"name": "split", 'start': 75, 'end': 100}
            ]
        }
    ]
    url = get_url('dataset-list', params=[('key', user.apikey.key)])
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    rdata = json.loads(response.content)
    idc = 0
    for i, entry in enumerate(rdata):
        entry.pop('created')
        idc += 1
        data[i].update({
            'id': idc,
            'shared': False,
            'last_column_is_output': None
        })
    assert rdata == data


def test_filters_invalid_type_split(client, get_url, data_file_list):
    df, df2, df3 = data_file_list
    user = df.user
    df2.user = user
    df2.save()
    df3.shared = True
    df3.save()
    count = DataSet.objects.count()
    data = [
        {
            'name': 'Train dataset',
            'data': df.pk,
            'filters': [
                {"name": "merge", "datas": [df2.pk, str(df3.pk)]},
                {"name": "split", 'start': 0, 'end': 75}
            ]
        }, {
            "name": "Test dataset",
            'data': df.pk,
            'filters': [
                {"name": "merge", "datas": [df2.pk, df3.pk]},
                {"name": "split", 'start': 75, 'end': '100'}
            ]
        }
    ]
    url = get_url('dataset-list', params=[('key', user.apikey.key)])
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert count == DataSet.objects.count()
    rdata = json.loads(response.content)
    print rdata


def test_filters_split_invalid_schema(client, get_url, data_file):
    user = data_file.user
    data = {
        'name': 'Big file',
        'data': data_file.pk,
        'filters': [
            {"name": "split", "start": 0, "end": 0}
        ]
    }
    url = get_url('dataset-list', params=[('key', user.apikey.key)])
    response = client.post(url, data=data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    rdata = json.loads(response.content)
    data = {'filters': [
        "Value 0 for field 'end' is less " "than minimum value: 1.000000"
    ]}
    assert rdata == data
