import pytest
import datetime
from dateutil import tz
from django.core.urlresolvers import reverse
from django.conf import settings
from rest_framework.test import APIClient
from core.utils import make_random_str
from web.models import ApiUser
from data_management.models import DataFile, ParseLog, DataSet
from job.models import TrainEnsemble

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """
    Creates new user with random email and password.
    Returns new user instance with password attribute.
    """

    name = (make_random_str() + '@' + make_random_str(4)
            + '.' + make_random_str(3)).lower()
    password = make_random_str(20)
    client_ = APIClient()
    client_.post(reverse('register'),
                 data={'username': name, 'password': password, 'password_repeat': password},
                 follow=True)
    user_ = ApiUser.objects.get(email=name)
    user_.password = password
    return user_


@pytest.fixture
def client():
    return APIClient()


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
def ensemble():
    """
    Return instance of empty ensemble
    """
    ds = data_set()
    ds2 = data_set()
    ensemble = TrainEnsemble.objects.create(
        user=ds.data.user,
        train_dataset=ds,
        test_dataset=ds2,
        data_type=TrainEnsemble.TIMESERIES
    )
    return ensemble


def test_ensemble_page(client, user, ensemble):
    response = client.get(reverse('view_train_ensemble',
                                  kwargs={'pk': ensemble.pk}), follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [
        ('http://testserver/?next=/train-ensemble/%s/' % ensemble.pk, 302)
    ]
    response = client.post(
        reverse('login'),
        data={'username': user.email, 'password': user.password}
    )
    assert response.status_code == 302
    response = client.get(reverse('view_train_ensemble',
                                  kwargs={'pk': ensemble.pk}), follow=True)
    assert response.status_code == 404
    user.is_superuser = True
    user.save()
    response = client.get(reverse('view_train_ensemble',
                                  kwargs={'pk': ensemble.pk}), follow=True)
    assert response.status_code == 200
