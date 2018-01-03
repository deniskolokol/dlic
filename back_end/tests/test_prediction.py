import StringIO
import gzip
import json
import pytest
import numpy as np
from fake_api import default_fake_api
from ersatz.dispatcher import ApiPredictDispatcher

def test_autoencoder_prediction_input_mode(autoencoder_input_api_message):
    with default_fake_api() as calls:
        ApiPredictDispatcher(autoencoder_input_api_message)
        assert len(calls) == 1
        body = json.loads(calls[0].body)
        assert body.has_key('results')
        assert len(body['results']['predictions']) == 1

        data = np.array(body['results']['predictions'][0]['output'])

        assert data.shape == (1, autoencoder_input_api_message['predicts'][0]\
            ['model_params']['hidden_outputs'])


def test_autoencoder_prediction_dataset_mode(autoencoder_dataset_api_message,
    save_modeldata_to_filename_mock):
    with default_fake_api() as calls:
        ApiPredictDispatcher(autoencoder_dataset_api_message)
        assert len(calls) == 1
        body = json.loads(calls[0].body)
        assert body.has_key('results')
        assert len(body['results']['predictions']) == 1
        assert save_modeldata_to_filename_mock.has_key('data')

        gzipped = save_modeldata_to_filename_mock['data']
        f = StringIO.StringIO(gzipped)
        gz = gzip.GzipFile(fileobj = f, mode = 'rb')

        csv = np.genfromtxt(gz, delimiter = ',')
        f.close()

        assert csv.shape[1] == autoencoder_dataset_api_message['predicts'][0]\
            ['model_params']['hidden_outputs']


@pytest.fixture(autouse = True)
def save_modeldata_to_filename_mock(monkeypatch):
    data = {}
    def local_save_modeldata(key, val):
        data['data'] = val
        return 's3_file_path'
    import ersatz.aws
    monkeypatch.setattr(ersatz.aws, 'save_modeldata_to_filename', local_save_modeldata)
    return data


@pytest.fixture
def autoencoder_model():
    return \
    {u'id': 1,
    u'iteration_id': 2,
    u'model_id': 1,
    u'model_name': u'AUTOENCODER',
    u'model_params': {u'batch_size': 128,
        u'hidden_outputs': 20},
    u'out_nonlin': u'SOFTMAX',
    u's3_data': u'fixtures/modeldata/autoencoder_turkish_20units.json.gz'}

@pytest.fixture
def autoencoder_data():
    return \
    {u'data': {u'classes': [[], [], [], [], [], [], [], []],
                u'data_type': u'GENERAL',
                u'delimiter': u'\\s*,\\s*',
                u'dtypes': [u'f',
                            u'f',
                            u'f',
                            u'f',
                            u'f',
                            u'f',
                            u'f',
                            u'f'],
                u'id': 1,
                u'key': u'dummy.csv.zip',
                u'num_columns': 8,
                u'with_header': True},
    u'filters': [{u'name': u'normalize'}],
    u'id': 1,
    u'iscreated': True,
    u'key': u'fixtures/dataset/Turkish_V1.hdf5',
    u'last_column_is_output': False,
    u'norm_min_max': None,
    u'quantiles': None,
    u'version': 1}

@pytest.fixture
def autoencoder_input_api_message(autoencoder_data, autoencoder_model):
    return \
    {u'data_type': u'GENERAL',
     u'dataset': autoencoder_data,
     u'ensemble': 1,
     u'input_data': u'-0.004679315,0.002193419,0.003894376,0,0.031190229,0.012698039,0.028524462,0.038376187',
     u'options': {},
     u'predicts': [autoencoder_model],
     u'quantiles': None,
     u'queue_key': u'e9af9b6e9d6ca5a51fe6ac5f112efcab66d9aa23',
     u'train_ensemble_id': 1}


@pytest.fixture
def autoencoder_dataset_api_message(autoencoder_data, autoencoder_model):
    return \
    {u'INPUT_ONLY': False,
    u'MODE': u'DATASET',
    u'data_type': u'GENERAL',
    u'dataset': autoencoder_data,
    u'ensemble': 1,
    u'options': {},
    u'predicts': [autoencoder_model],
    u'quantiles': None,
    u'queue_key': u'cf30d70bf0c1ae392d6a68e0b0e5fcad74175236',
    u'train_ensemble_id': 1}
