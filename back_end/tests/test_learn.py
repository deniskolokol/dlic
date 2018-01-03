import unittest
import json
import StringIO
from zipfile import ZipFile
import mock
import numpy as np
from fake_api import fake_api
from mocks import upload_modeldata_mock
from ersatz import aws
from ersatz.pylearn.runners import TrainRunner, PylearnPredictRunner
from ersatz.conf import settings, get_api_port


class ReportStatsTracker(object):

    def __init__(self):
        self.stats = None
        self.upload_modeldata = []
        self.modeldata = []

    def __call__(self, modeldata, stats, upload_modeldata=False):
        self.stats = stats
        self.upload_modeldata.append(upload_modeldata)
        self.modeldata.append(modeldata)


class ReportResultMock(object):

    def __init__(self):
        self.result = None

    def __call__(self, result):
        self.result = result


class TestLrMomentum(unittest.TestCase):

    def setUp(self):
        self.train_datafile = 'fixtures/csv/iris.csv.zip'
        self.queue_key = u'de5007e4c797cf2153581779e6950216e76fc9c4'
        self.s3_data_1 = 'fixtures/modeldata/rl_iris_15_iters.pkl.gz'

    def response(self, path, data, server, *args, **kwargs):
        data = json.loads(data)
        if 'data' in data and data['data'].get('iteration') == 5 and False:
            server.send_error(400, 'Bad request')
        return json.dumps({'status': 'success'})

    def test_learning_rate_update(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'file_name': self.train_datafile,
            u'data_split': [80, 20, 0],
            u'sp_results': u'',
            u'ensemble': 1,
            u'test_dataset': None,
            u'quantiles': None,
            u'config': None,
            u'queue_key': self.queue_key,
            u'options': {},
            u'models': [{
                u'out_nonlin': u'',
                u'id': 2,
                u'name': u'MLP_RECTIFIED',
                u'model_params': {
                    u'maxnum_iter': 15,
                    u'percent_batches_per_iter': 100,
                    u'save_freq': 10,
                    u'layers': [
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h0',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h1',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                    ],
                    u'learning_rate': {
                        u'init': 0.1,
                        u'final': 1e-06,
                        u'decay_factor': 1.00004,
                        u'constant': False
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.5,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 10,
                        u'constant': False
                    }
                },
            }]
        }
        runner = TrainRunner(api_message)
        with fake_api(port=get_api_port(), default_response=self.response) as calls:
            with upload_modeldata_mock():
                runner.train_models()
                last = json.loads(calls[-2].body)['data']
                iteration = last['iteration']
                self.assertEqual(14, iteration)
                lr_i = last['outputs_header'].index('learning_rate')
                momentum_i = last['outputs_header'].index('momentum')
                lr = last['train_outputs'][0][lr_i]
                momentum = last['train_outputs'][0][momentum_i]
                self.assertAlmostEqual(lr, 0.1)
                self.assertAlmostEqual(momentum, 0.5)
                lr = last['train_outputs'][10][lr_i]
                momentum = last['train_outputs'][10][momentum_i]
                self.assertAlmostEqual(lr, 1e-06)
                self.assertAlmostEqual(momentum, 0.95)
                lr = last['train_outputs'][1][lr_i]
                momentum = last['train_outputs'][1][momentum_i]
                lr_ = 0.1 - (0.1 - 1e-06) / 10
                momentum_ = 0.5 + (0.95 - 0.5) / 10
                self.assertAlmostEqual(lr, lr_, places=4)
                self.assertAlmostEqual(momentum, momentum_, places=4)
                lr = last['train_outputs'][5][lr_i]
                momentum = last['train_outputs'][5][momentum_i]
                lr_ = 0.1 - (0.1 - 1e-06) / 10 * 5
                momentum_ = 0.5 + (0.95 - 0.5) / 10 * 5
                self.assertAlmostEqual(lr, lr_, places=4)
                self.assertAlmostEqual(momentum, momentum_, places=4)
                lr = last['train_outputs'][-1][lr_i]
                momentum = last['train_outputs'][-1][momentum_i]
                self.assertAlmostEqual(lr, 1e-06)
                self.assertAlmostEqual(momentum, 0.95)

    def test_learning_rate_constant(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'file_name': self.train_datafile,
            u'data_split': [80, 20, 0],
            u'sp_results': u'',
            u'ensemble': 1,
            u'test_dataset': None,
            u'quantiles': None,
            u'config': None,
            u'queue_key': self.queue_key,
            u'options': {},
            u'models': [{
                u'out_nonlin': u'',
                u'id': 2,
                u'name': u'MLP_RECTIFIED',
                u'model_params': {
                    u'maxnum_iter': 15,
                    u'percent_batches_per_iter': 100,
                    u'save_freq': 10,
                    u'layers': [
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h0',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h1',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                    ],
                    u'learning_rate': {
                        u'init': 0.1,
                        u'final': 1e-06,
                        u'decay_factor': 1.00004,
                        u'constant': True
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.5,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 10,
                        u'constant': True
                    }
                },
            }]
        }
        runner = TrainRunner(api_message)
        with fake_api(port=get_api_port(), default_response=self.response) as calls:
            with upload_modeldata_mock():
                runner.train_models()
                last = json.loads(calls[-2].body)['data']
                iteration = last['iteration']
                self.assertEqual(14, iteration)
                lr_i = last['outputs_header'].index('learning_rate')
                momentum_i = last['outputs_header'].index('momentum')
                for o in last['train_outputs']:
                    self.assertAlmostEqual(0.1, o[lr_i])
                    self.assertAlmostEqual(0.5, o[momentum_i])

    def test_learning_rate_update_const(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'file_name': self.train_datafile,
            u'data_split': [80, 20, 0],
            u'sp_results': u'',
            u'ensemble': 1,
            u'test_dataset': None,
            u'quantiles': None,
            u'config': None,
            u'queue_key': self.queue_key,
            u'options': {},
            u'models': [{
                u'out_nonlin': u'',
                u'id': 2,
                u'name': u'MLP_RECTIFIED',
                u'resume_X': self.s3_data_1,
                u'resume': True,
                u'model_params': {
                    u'maxnum_iter': 17,
                    u'percent_batches_per_iter': 100,
                    u'save_freq': 10,
                    u'layers': [
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h0',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                        {
                            u'type': u'rectified_linear',
                            u'layer_name': u'h1',
                            u'dim': 200,
                            u'sparse_init': 10
                        },
                    ],
                    u'learning_rate': {
                        u'init': 0.2,
                        u'final': 1e-06,
                        u'decay_factor': 1.00004,
                        u'constant': True
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.99,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 10,
                        u'constant': True
                    }
                },
            }]
        }
        runner = TrainRunner(api_message)
        with fake_api(port=get_api_port(), default_response=self.response) as calls:
            with upload_modeldata_mock():
                runner.train_models()
                last = json.loads(calls[-2].body)['data']
                iteration = last['iteration']
                self.assertEqual(16, iteration)
                lr_i = last['outputs_header'].index('learning_rate')
                momentum_i = last['outputs_header'].index('momentum')
                o = last['train_outputs']
                self.assertAlmostEqual(0.2, o[-2][lr_i], places=4)
                self.assertAlmostEqual(0.99, o[-2][momentum_i], places=4)
                self.assertAlmostEqual(0.2, o[-1][lr_i], places=4)
                self.assertAlmostEqual(0.99, o[-1][momentum_i], places=4)



class TestMaxout(unittest.TestCase):

    def setUp(self):
        self.train_datafile = 'fixtures/mnist/train_full.csv.zip'
        self.s3_data_1 = 'fixtures/modeldata/maxout_mnist_15_iters.pkl.gz'
        self.s3_data_2 = 'fixtures/modeldata/maxout_mnist_50_iters.pkl.gz'
        self.valid_datafile = 'fixtures/mnist/valid_full.csv.zip'
        self.queue_key = u'de5007e4c797cf2153581779e6950216e76fc9c4'

    def test_mnist_train(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'file_name': self.train_datafile,
            u'data_split': [100, 0, 0],
            u'sp_results': u'',
            u'ensemble': 1,
            u'test_dataset': self.valid_datafile,
            u'quantiles': None,
            u'config': None,
            u'queue_key': self.queue_key,
            u'options': {},
            u'models': [{
                u'out_nonlin': u'',
                u'id': 2,
                u'name': u'MLP_MAXOUT',
                u'model_params': {
                    u'maxnum_iter': 15,
                    u'percent_batches_per_iter': 100,
                    u'save_freq': 10,
                    u'layers': [
                        {
                            u'num_pieces': 2,
                            u'max_col_norm': 1.9365,
                            u'layer_name': u'h0',
                            u'irange': 0.005,
                            u'type': u'maxout',
                            u'num_units': 240
                        },
                        {
                            u'num_pieces': 2,
                            u'max_col_norm': 1.9365,
                            u'layer_name': u'h1',
                            u'irange': 0.005,
                            u'type': u'maxout',
                            u'num_units': 240
                        },
                        {
                            u'num_pieces': 2,
                            u'max_col_norm': 1.9365,
                            u'layer_name': u'h2',
                            u'irange': 0.005,
                            u'type': u'maxout',
                            u'num_units': 240
                        }
                    ],
                    u'learning_rate': {
                        u'init': 0.1,
                        u'final': 1e-06,
                        u'decay_factor': 1.00004,
                        u'constant': False
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.5,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 20,
                        u'constant': False
                    }
                },
            }]
        }
        runner = TrainRunner(api_message)
        response = mock.Mock()
        response.status_code = 200
        response.text = {'status': 'success'}
        tracker = ReportStatsTracker()
        with mock.patch('requests.post') as patched_post:
            with upload_modeldata_mock():
                with mock.patch.object(TrainRunner, 'report_stats', tracker):
                    patched_post.return_value = response
                    runner.train_models()
        upload_modeldata = [False] * 15
        upload_modeldata[0] = True
        upload_modeldata[9] = True
        upload_modeldata[14] = True
        self.assertEqual(tracker.upload_modeldata, upload_modeldata)
        iters = [x[0] for x in tracker.stats['train_outputs']]
        train_accs = [x[1] for x in tracker.stats['train_outputs']]
        test_accs = [x[2] for x in tracker.stats['train_outputs']]
        self.assertEqual(tracker.stats['iteration'], 14)
        self.assertEqual(iters, range(15))
        self.assertEqual(len(train_accs), 15)
        self.assertEqual(len(test_accs), 15)
        self.assertTrue(tracker.stats['train_accuracy'] > 97.2)
        self.assertTrue(tracker.stats['test_accuracy'] > 96.8)
        # report start args
        url, api_params = patched_post.mock_calls[0][1]
        api_params = json.loads(api_params)
        self.assertEqual(url, settings.API_SERVER + '/api/train/status/')
        self.assertEqual(api_params['worker_key'], settings.WORKER_KEY)
        self.assertEqual(api_params['queue_key'], self.queue_key)
        self.assertEqual(api_params['state'], 'TRAIN')
        # report finish args
        url, api_params = patched_post.mock_calls[1][1]
        api_params = json.loads(api_params)
        self.assertEqual(url, settings.API_SERVER + '/api/train/status/')
        self.assertEqual(api_params['worker_key'], settings.WORKER_KEY)
        self.assertEqual(api_params['queue_key'], self.queue_key)
        self.assertEqual(api_params['state'], 'FINISHED')


    def test_mnist_resume(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'file_name': self.train_datafile,
            u'data_split': [100, 0, 0],
            u'sp_results': u'',
            u'ensemble': 50,
            u'test_dataset': self.valid_datafile,
            u'quantiles': None,
            u'config': None,
            u'queue_key': self.queue_key,
            u'options': None,
            u'models': [{
                u'resume_X': self.s3_data_1,
                u'name': u'MLP_MAXOUT',
                u'lower_loss': None,
                u'resume': True,
                u'high_score': 0.993200003169477,
                u'out_nonlin': u'',
                u'id': 52,
                u'model_params': {
                    u'maxnum_iter': 20,
                    u'percent_batches_per_iter': 100,
                    u'save_freq': 5,
                    u'layers': [
                        {'type': 'maxout',
                         'layer_name': 'h0',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        },
                        {'type': 'maxout',
                         'layer_name': 'h1',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        },
                        {'type': 'maxout',
                         'layer_name': 'h2',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        }
                    ],
                    u'learning_rate': {
                        u'init': 0.05,
                        u'final': 1e-06,
                        u'decay_factor': 1.00004,
                        u'constant': False
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.5,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 20,
                        u'constant': False
                    }
                }
            }]
        }
        runner = TrainRunner(api_message)
        response = mock.Mock()
        response.status_code = 200
        response.text = {'status': 'success'}
        tracker = ReportStatsTracker()
        with mock.patch('requests.post') as patched_post:
            with upload_modeldata_mock():
                with mock.patch.object(TrainRunner, 'report_stats', tracker):
                    patched_post.return_value = response
                    runner.train_models()
        self.assertEqual(tracker.upload_modeldata, [False, False, False, False, True])
        iters = [x[0] for x in tracker.stats['train_outputs']]
        train_accs = [x[1] for x in tracker.stats['train_outputs']]
        test_accs = [x[2] for x in tracker.stats['train_outputs']]
        self.assertEqual(tracker.stats['iteration'], 19)
        self.assertEqual(iters, range(20))
        self.assertEqual(len(train_accs), 20)
        self.assertEqual(len(test_accs), 20)
        self.assertTrue(tracker.stats['train_accuracy'] > 97.5)
        self.assertTrue(tracker.stats['test_accuracy'] > 97.2)
        # report start args
        url, api_params = patched_post.mock_calls[0][1]
        api_params = json.loads(api_params)
        self.assertEqual(url, settings.API_SERVER + '/api/train/status/')
        self.assertEqual(api_params['worker_key'], settings.WORKER_KEY)
        self.assertEqual(api_params['queue_key'], self.queue_key)
        self.assertEqual(api_params['state'], 'TRAIN')
        # report finish args
        url, api_params = patched_post.mock_calls[1][1]
        api_params = json.loads(api_params)
        self.assertEqual(url, settings.API_SERVER + '/api/train/status/')
        self.assertEqual(api_params['worker_key'], settings.WORKER_KEY)
        self.assertEqual(api_params['queue_key'], self.queue_key)
        self.assertEqual(api_params['state'], 'FINISHED')

    def test_predict(self):
        input_data = aws.S3Key(self.valid_datafile).get()
        with ZipFile(input_data, 'r') as z:
            with z.open(z.namelist()[0]) as f:
                input_data = np.loadtxt(f)[:1000]
        output_data = input_data[:, -1]
        input_data = input_data[:, :-1]
        temp = StringIO.StringIO('')
        np.savetxt(temp, input_data)
        temp.seek(0)
        input_data = temp.read()

        api_message = {
            u'data_type': u'GENERAL',
            u'train_ensemble_id': 50,
            u'ensemble': 445,
            u'input_data': input_data,
            u'quantiles': None,
            u'predicts': [{
                u'model_id': 52,
                u'model_params': {
                    u'maxnum_iter': 6,
                    u'save_freq': 2,
                    u'layers': [
                        {'type': 'maxout',
                         'layer_name': 'h0',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        },
                        {'type': 'maxout',
                         'layer_name': 'h1',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        },
                        {'type': 'maxout',
                         'layer_name': 'h2',
                         'num_units': 240,
                         'num_pieces': 2,
                         'irange': 0.005,
                         'max_col_norm': 1.9365,
                        }
                    ],
                    u'learning_rate': {
                        u'init': 0.05,
                        u'final': 1e-06,
                        u'start': 1,
                        u'stop': 20,
                    },
                    u'batch_size': 128,
                    u'momentum': {
                        u'init': 0.5,
                        u'final': 0.95,
                        u'start': 1,
                        u'stop': 20,
                    }
                },
                u'id': 446,
                u'out_nonlin': u'',
                u'model_name': u'MLP_MAXOUT',
                u's3_data': self.s3_data_2
            }],
            u'queue_key': u'68076b8f5d648ae7bcd6031335d4fc1c8bb14b35',
            u'options': None
        }
        runner = PylearnPredictRunner(api_message)
        response = mock.Mock()
        response.status_code = 200
        response.text = {'status': 'success'}
        tracker = ReportResultMock()
        with mock.patch.object(PylearnPredictRunner, 'report_result', tracker):
            runner.predict_models()
        acc = (tracker.result['predicts'][446]['results'] == output_data)
        acc = acc.astype('int').sum() / float(acc.shape[0])
        self.assertTrue(acc > 0.98)
