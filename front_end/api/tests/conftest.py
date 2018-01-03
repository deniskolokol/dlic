"""
Provides fixtures for all api tests.
"""

import datetime
import json
import mock
import redis
import pika
import pytest
from dateutil import tz
from celery import Celery
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.storage import default_storage
from rest_framework.test import APIClient
from boto import s3
from web.models import ApiUser
from data_management.models import DataFile, ParseLog, DataSet
from job.models import TrainEnsemble, LearnModel, DeepNetModel
from core.utils import make_random_str


@pytest.fixture(autouse=True)
def patch_redis(request, monkeypatch):
    monkeypatch.setattr(redis, 'StrictRedis', mock.MagicMock())


@pytest.fixture(autouse=True)
def patch_file_field_save(request, monkeypatch):
    monkeypatch.setattr(default_storage, 'save',
                        lambda name, content, save=True: name)


@pytest.fixture(autouse=True)
def patch_queue(request, monkeypatch):
    queue = []
    calls = []

    def basic_publish(*args, **kwargs):
        queue.append(json.loads(kwargs['body']))
        calls.append((args, kwargs))

    channel_mock = mock.MagicMock()
    channel_mock.basic_publish = basic_publish
    attrs = {'return_value.channel.return_value': channel_mock}
    connection_mock = mock.MagicMock()
    connection_mock.configure_mock(**attrs)
    monkeypatch.setattr(pika, 'BlockingConnection', connection_mock)
    return {'queue': queue, 'calls': calls}


@pytest.fixture(autouse=True)
def patch_upload_data_to_s3(request, monkeypatch):
    obj = mock.MagicMock()
    monkeypatch.setattr(s3.connection, 'S3Connection', mock.MagicMock())
    monkeypatch.setattr(s3.key, 'Key', obj)
    return obj


@pytest.fixture(autouse=True)
def patch_celery(request, monkeypatch):
    class AsyncResultMock(object):
        def __init__(self):
            self.id = 'celery_result_id'
    obj = mock.MagicMock(return_value=AsyncResultMock())
    monkeypatch.setattr(Celery, 'send_task', obj)
    return obj


@pytest.fixture
def get_url():
    def f(viewname, params=None, **kwargs):
        """
        params is list of url params: params=[(key, val), ...] -> ?key=val&...
        """
        url = reverse(viewname, **kwargs)
        if params:
            params = '?' + '&'.join(str(x) + '=' + str(y) for x, y in params)
            return url + params
        return url
    return f


@pytest.fixture
def user():
    """
    Creates new user with random email and password.
    Returns new user instance with password attribute.
    """

    name = (make_random_str() + '@' + make_random_str(4) +
            '.' + make_random_str(3)).lower()
    password = make_random_str(20)
    client_ = APIClient()
    client_.post(reverse('register'),
                 data={'username': name, 'password': password,
                       'password_repeat': password},
                 follow=True)
    user_ = ApiUser.objects.get(email=name)
    user_.password = password
    return user_


@pytest.fixture
def client():
    """
    Returns instance of Client
    """

    return APIClient()


@pytest.yield_fixture
@pytest.fixture(scope="class")
def class_setup(request, patch_queue):
    """
    Provide user and client fixtures for TestCases tests
    """
    request.cls.user = user()
    request.cls.client = client()
    request.cls.patch_queue = patch_queue
    yield None
    request.cls.user.delete()


@pytest.fixture
def data_file():
    """
    Returns instance of DataFile, also creates user
    """
    user_ = user()
    df_key = "uploads/1/" + make_random_str(8) + "/manualxts.zip"
    meta = {
        "archive_path": "manualx.ts",
        "data_rows": 32,
        "output_size": 2,
        "data_type": "TIMESERIES",
        "binary_output": True,
        "binary_input": False,
        "min_timesteps": 95,
        "empty_rows": 0,
        "version": 3,
        "key": df_key,
        "max_timesteps": 97,
        "input_size": 2,
        "classes": {
            "1": 121,
            "0": 2951
        },
        "size": 6002
    }

    timestamp = datetime.datetime.utcnow().replace(tzinfo=tz.tzutc())
    df = DataFile.objects.create(user=user_,
                                 key=df_key,
                                 file_format='TIMESERIES',
                                 name='test.ts',
                                 state=DataFile.STATE_READY,
                                 meta=meta)
    for i in range(3):
        timestamp += datetime.timedelta(1)
        ParseLog.objects.create(timestamp=timestamp,
                                message='Log entry #%s' % i,
                                data_file=df)
    return df


@pytest.fixture
def data_file_ts():
    return data_file()


@pytest.fixture
def data_file_images():
    user_ = user()
    df_key = "uploads/1/" + make_random_str(8) + "/data.zip"
    meta = {
        'data_type': 'IMAGES',
        'size': 100,
        'classes': {'class1': 2, 'class2': 3}
    }
    timestamp = datetime.datetime.utcnow().replace(tzinfo=tz.tzutc())
    df = DataFile.objects.create(user=user_,
                                 key=df_key,
                                 file_format='IMAGES',
                                 name='images my',
                                 state=DataFile.STATE_READY,
                                 meta=meta)
    for i in range(3):
        timestamp += datetime.timedelta(1)
        ParseLog.objects.create(timestamp=timestamp,
                                message='Log entry #%s' % i,
                                data_file=df)
    return df


@pytest.fixture
def data_file_csv():
    """
    Returns instance of DataFile, also creates user
    """
    user_ = user()
    df_key = "uploads/1/" + make_random_str(8) + "/iris.csv.zip"
    meta = {
        'version': 3,
        'data_type': 'GENERAL',
        'key': df_key,
        'size': 100,
        'archive_path': 'iris.csv',
        'data_rows': 6,
        'empty_rows': 0,
        'num_columns': 4,
        'delimeter': '\s*,\s*',
        'with_header': False,
        'last_column_info': {
            'max': 2.,
            'min': 0.,
            'unique': 3,
            'classes': {'0': 3, '1': 2, '2': 1}
        }
    }
    timestamp = datetime.datetime.utcnow().replace(tzinfo=tz.tzutc())
    df = DataFile.objects.create(user=user_,
                                 key=df_key,
                                 file_format='GENERAL',
                                 name='Data',
                                 state=DataFile.STATE_READY,
                                 meta=meta)
    for i in range(3):
        timestamp += datetime.timedelta(1)
        ParseLog.objects.create(timestamp=timestamp,
                                message='Log entry #%s' % i,
                                data_file=df)
    return df


@pytest.fixture
def data_file_csv_columns():
    """
    Returns instance of DataFile, also creates user
    """
    user_ = user()
    df_key = "uploads/1/" + make_random_str(8) + "/iris.csv.zip"
    meta = {
        'version': 3,
        'data_type': 'GENERAL',
        'key': df_key,
        'size': 100,
        'archive_path': 'iris.csv',
        'data_rows': 6,
        'empty_rows': 0,
        'num_columns': 4,
        'delimeter': '\s*,\s*',
        'with_header': False,
        'last_column_info': {
            'max': 2.,
            'min': 0.,
            'unique': 3,
            'classes': {'0': 3, '1': 2, '2': 1}
        },
        "names": ["1", "2", "3", "4"],
        "dtypes": ["f", "i", "f", "S"]

    }
    timestamp = datetime.datetime.utcnow().replace(tzinfo=tz.tzutc())
    df = DataFile.objects.create(user=user_,
                                 key=df_key,
                                 file_format='GENERAL',
                                 name='Data',
                                 state=DataFile.STATE_READY,
                                 meta=meta)
    for i in range(3):
        timestamp += datetime.timedelta(1)
        ParseLog.objects.create(timestamp=timestamp,
                                message='Log entry #%s' % i,
                                data_file=df)
    return df


@pytest.fixture
def data_set():
    """
    Returns instance of DataSet, also creates DataFile and ApiUser
    """

    df = data_file()
    filters = [
        {"name": "shuffle"},
    ]
    key = "uploads/datasets/1/" + make_random_str(8) + "/manualxts.zip"
    ds = DataSet.objects.create(data=df, filters=filters,
                                user=df.user,
                                name='test.csv.zip', key=key)
    return ds


@pytest.fixture
def data_set_ts():
    df = data_file_ts()
    filters = []
    ds = DataSet.objects.create(data=df, filters=filters,
                                user=df.user,
                                name='My File', key='datasets/' + df.key)
    return ds


@pytest.fixture
def data_set_csv():
    df = data_file_csv()
    filters = []
    ds = DataSet.objects.create(data=df, filters=filters,
                                user=df.user,
                                last_column_is_output=True,
                                name='My csv', key='datasets/' + df.key)
    return ds


@pytest.fixture
def data_set_images():
    df = data_file_images()
    filters = []
    ds = DataSet.objects.create(data=df, filters=filters,
                                user=df.user,
                                name='My images', key='datasets/' + df.key)
    return ds


@pytest.fixture
def get_data_set_ts():
    return data_set_ts


@pytest.fixture
def get_data_set_csv():
    return data_set_csv


@pytest.fixture
def get_data_set_images():
    return data_set_images


@pytest.fixture
def ensemble():
    """
    Return instance of empty ensemble
    """
    ds = data_set()
    ds2 = data_set_ts()
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.TIMESERIES,
        net_type=TrainEnsemble.NET_RNN,
    )
    return ensemble


@pytest.fixture
def ensemble_mrnn():
    """
    Returns instance of mrnn ensemble with one model
    """
    ens = ensemble()
    LearnModel.objects.create(
        ensemble=ens,
        model_name='MRNN'
    )
    return ens


@pytest.fixture
def ensemble_autoencoder():
    """
    Returns instance of autoencoder ensemble with one model
    """
    ds = data_set_csv()
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        data_type=TrainEnsemble.GENERAL,
        net_type=TrainEnsemble.NET_AUTOENCODER,
    )
    LearnModel.objects.create(
        ensemble=ensemble,
        model_name='AUTOENCODER'
    )
    return ensemble


@pytest.fixture
def ensemble_mlp_sigmoid():
    """
    Returns instance of sigmoid ensemble with one model
    """
    ds = data_set_csv()
    ds2 = DataSet.objects.create(data=ds.data, filters=[],
                                 user=ds.user,
                                 last_column_is_output=True,
                                 name='test.csv.zip', key='asd2')
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.GENERAL,
        net_type=TrainEnsemble.NET_DEEPNET,
    )
    LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MLP_SIGMOID'
    )
    return ensemble


@pytest.fixture
def trained_mlp_ensemble():
    """
    Returns instance of mlp_maxout_conv with two trained models
    """
    ds = data_set_csv()
    ds2 = DataSet.objects.create(data=ds.data, filters=[],
                                 last_column_is_output=True,
                                 user=ds.user,
                                 name='test.csv.zip', key='asd3')
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.GENERAL,
        net_type=TrainEnsemble.NET_DEEPNET,
    )
    lm1 = DeepNetModel.objects.create(
        ensemble=ensemble,
        model_name='MLP_MAXOUT_CONV'
    )
    lm2 = DeepNetModel.objects.create(
        ensemble=ensemble,
        model_name='MLP_MAXOUT_CONV'
    )
    data = {
        'iteration': 10,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    lm1.add_stat(data, '/s3.key')
    lm1.to_finish_state('1 2 3 4')
    data = {
        'iteration': 100,
        'train_accuracy': 0.5,
        'test_accuracy': 0.4,
        'time': 20,
    }
    lm2.add_stat(data, '/s3.key2')
    lm2.to_finish_state('21 23 23 24')
    return ensemble


@pytest.fixture
def trained_images_ensemble():
    """
    Returns instance of CONV with two trained models
    """
    ds = data_set_images()
    ds2 = DataSet.objects.create(data=ds.data, filters=[],
                                 user=ds.user,
                                 name='test.csv', key='asd3')
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.IMAGES,
        net_type=TrainEnsemble.NET_DEEPNET,
    )
    lm1 = DeepNetModel.objects.create(
        ensemble=ensemble,
        model_name='CONV'
    )
    lm2 = DeepNetModel.objects.create(
        ensemble=ensemble,
        model_name='CONV'
    )
    data = {
        'iteration': 10,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    lm1.add_stat(data, '/s3.key')
    lm1.to_finish_state('1 2 3 4')
    data = {
        'iteration': 100,
        'train_accuracy': 0.5,
        'test_accuracy': 0.4,
        'time': 20,
    }
    lm2.add_stat(data, '/s3.key2')
    lm2.to_finish_state('1 3 3 4')
    return ensemble


@pytest.fixture
def trained_mrnn_ensemble():
    """
    Returns instance of TIMESERIES ensemble with two trained models
    """

    ds = data_set_ts()
    ds2 = DataSet.objects.create(data=ds.data,
                                 filters=[],
                                 user=ds.user,
                                 name='test.ts.zip',
                                 key=make_random_str(8))
    ensemble = TrainEnsemble.objects.create(
        user=ds.user,
        out_nonlin="SOFTMAX",
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.TIMESERIES,
        net_type=TrainEnsemble.NET_DEEPNET,
    )
    lm1 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN',
        model_params={'maxnum_iter': 20},
    )
    lm2 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN',
        model_params={'maxnum_iter': 20},
    )
    data = {
        'iteration': 1,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    lm1.add_stat(data, '/s3.keya213')
    data.update({'iteration': 2, 'train_accuracy': 0.91})
    lm1.add_stat(data, '/s3.keyasdfadsf')
    data.update({'iteration': 3, 'train_accuracy': 0.95})
    lm1.add_stat(data, '/s3.keyasdfadsfsd')
    lm1.to_finish_state('1 2 3 4', '')
    data = {
        'iteration': 1,
        'train_accuracy': 0.5,
        'test_accuracy': 0.4,
        'time': 20,
    }
    lm2.add_stat(data, '/s3.key2sdsd')
    lm2.to_finish_state('1 3 3 4', '')
    return ensemble


@pytest.fixture
def get_trained_mrnn_ensemble():
    def f():
        return trained_mrnn_ensemble()
    return f


@pytest.fixture
def ensemble_all_types():
    """
    Return all types of ensembles-models
    """

    models = ['MRNN', 'CONV', 'AUTOENCODER', 'MLP_SIGMOID', 'MLP_RECTIFIED',
              'MLP_MAXOUT', 'MLP_MAXOUT_CONV']

    ensembles_models = []

    dataset = data_set()
    test = data_set()
    df = test.data
    df.user = dataset.data.user
    df.save()

    for x in models:

        if x == 'MRNN':
            d_type = TrainEnsemble.TIMESERIES
        elif x == 'CONV':
            d_type = TrainEnsemble.IMAGES
        else:
            d_type = TrainEnsemble.GENERAL

        ensemble = TrainEnsemble.objects.create(
            user=dataset.data.user,
            train_dataset=dataset,
            test_dataset=test,
            data_type=d_type
        )

        LearnModel.objects.create(
            ensemble=ensemble,
            model_name=x
        )

        ensembles_models.append(ensemble)

    return ensembles_models


@pytest.fixture
def data_file_list():
    """
    Returns list of data files with different users
    """

    df1 = data_file()
    df2 = data_file()
    df3 = data_file()
    return [df1, df2, df3]
