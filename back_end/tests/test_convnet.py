import unittest
import json
from .fake_api import fake_api
from ersatz import aws
from ersatz.runners import ImageEnsembleRunner
from ersatz.predictors import predict_convnet
from ersatz.conf import get_api_port, settings
from ersatz.shared.cifar import construct_predict_batch

class TestConvnet(unittest.TestCase):

    def test_train(self):
        api_message = {
            u'data_type': u'IMAGES',
            u'models': [{
                u'model_params': {
                    u'maxnum_iter': 20,
                    u'save_freq': 15,
                    u'img_size': 32,
                    u'test_freq': 10,
                    u'layers': u'[data]\ntype=data\ndataidx=0\n[labels]\ntype=data\ndataidx=1\n[conv1]\ntype=conv\ninputs=data\nchannels=3\nfilters=32\npadding=2\nstride=1\nfiltersize=5\ninitw=0.0001\npartialsum=4\nsharedbiases=1\n[pool1]\ntype=pool\npool=max\ninputs=conv1\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\nneuron=relu\n[rnorm1]\ntype=rnorm\ninputs=pool1\nchannels=32\nsize=3\n[conv2]\ntype=conv\ninputs=rnorm1\nfilters=32\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool2]\ntype=pool\npool=avg\ninputs=conv2\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\n[rnorm2]\ntype=rnorm\ninputs=pool2\nchannels=32\nsize=3\n[conv3]\ntype=conv\ninputs=rnorm2\nfilters=64\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool3]\ntype=pool\npool=avg\ninputs=conv3\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=64\n[fc10]\ntype=fc\noutputs=10\ninputs=pool3\ninitw=0.01\n[probs]\ntype=softmax\ninputs=fc10\n[logprob]\ntype=cost.logreg\ninputs=labels,probs',
                    u'layer_params': u'[conv1]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\nnepsw=0.001\n[conv2]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[conv3]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[fc10]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=1\n[logprob]\ncoeff=1\n[rnorm1]\nscale=0.00005\npow=.75\n[rnorm2]\nscale=0.00005\npow=.75'
                },
                u'out_nonlin': None,
                u'id': 10,
                u'name': u'CONV'
            }],
            u'file_name': u'fixtures/images/animals.zip',
            u'data_split': [80, 20],
            u'sp_results': u'',
            u'options': {},
            u'quantiles': None,
            u'config': None,
            u'queue_key': u'490c36dd7437bda9bfd9e40abad585d68def5470',
            u'ensemble': 2
        }

        runner = ImageEnsembleRunner(api_message)
        with fake_api(port=get_api_port(), default_response=json.dumps({'status': 'success'})) as calls:
            runner.train_models()
            # first call
            self.assertEqual(calls[0].path, '/api/train/status/')
            data = json.loads(calls[0].body)
            self.assertEqual(data['state'], 'TRAIN')
            self.assertEqual(data['model_name'], 'CONV')
            self.assertEqual(data['queue_key'], api_message['queue_key'])
            self.assertEqual(data['model'], api_message['models'][0]['id'])
            self.assertEqual(data['worker_key'], settings.WORKER_KEY)
            self.assertEqual(data['model_params']['maxnum_iter'],
                             api_message['models'][0]['model_params']['maxnum_iter'])
            # last call
            self.assertEqual(calls[4].path, '/api/train/status/')
            data = json.loads(calls[4].body)
            self.assertEqual(data['state'], 'FINISHED')
            self.assertEqual(data['model_name'], 'CONV')
            self.assertEqual(data['queue_key'], api_message['queue_key'])
            self.assertEqual(data['model'], api_message['models'][0]['id'])
            self.assertEqual(data['worker_key'], settings.WORKER_KEY)
            # second call (stats)
            self.assertEqual(calls[1].path, '/api/stats/')
            data = json.loads(calls[1].body)
            self.assertEqual(data['model_name'], 'CONV')
            self.assertEqual(data['queue_key'], api_message['queue_key'])
            self.assertEqual(data['model'], api_message['models'][0]['id'])
            self.assertEqual(data['worker_key'], settings.WORKER_KEY)
            self.assertEqual(data['data']['iteration'], 9)
            self.assertTrue(data['data']['train_accuracy'] > 0.35)
            self.assertTrue(data['data']['test_accuracy'] > 0.30)
            self.assertEqual(len(data['data']['test_outputs']), 1)
            self.assertEqual(len(data['data']['test_outputs'][0]), 3)
            self.assertEqual(len(data['data']['train_outputs']), 10)
            self.assertEqual(len(data['data']['train_outputs'][0]), 2)
            labels = [u'alligator', u'ant', u'bear', u'beaver', u'dolphin',
                      u'frog', u'giraffe', u'leopard', u'monkey', u'penguin']
            self.assertEqual(data['data']['label_names'], labels)
            # third call (stats)
            self.assertEqual(calls[2].path, '/api/stats/')
            data = json.loads(calls[2].body)
            self.assertEqual(data['model_name'], 'CONV')
            self.assertEqual(data['queue_key'], api_message['queue_key'])
            self.assertEqual(data['model'], api_message['models'][0]['id'])
            self.assertEqual(data['worker_key'], settings.WORKER_KEY)
            self.assertEqual(data['data']['iteration'], 14)
            self.assertTrue(data['data']['train_accuracy'] > 0.40)
            self.assertTrue(data['data']['test_accuracy'] > 0.33)
            self.assertEqual(len(data['data']['test_outputs']), 2)
            self.assertEqual(len(data['data']['train_outputs']), 15)
            # fourth call (stats)
            self.assertEqual(calls[3].path, '/api/stats/')
            data = json.loads(calls[3].body)
            self.assertEqual(data['model_name'], 'CONV')
            self.assertEqual(data['queue_key'], api_message['queue_key'])
            self.assertEqual(data['model'], api_message['models'][0]['id'])
            self.assertEqual(data['worker_key'], settings.WORKER_KEY)
            self.assertEqual(data['data']['iteration'], 19)
            self.assertTrue(data['data']['train_accuracy'] > 0.42)
            self.assertTrue(data['data']['test_accuracy'] > 0.36)
            self.assertEqual(len(data['data']['test_outputs']), 3)
            self.assertEqual(len(data['data']['train_outputs']), 20)

    def test_predict(self):
        api_message =  {
            u'data_type': u'IMAGES',
            u'input_data': u'',
            u'file_name': u'fixtures/images/animals.zip',
            u'ensemble': 1,
            u'train_ensemble_id': 1,
            u'quantiles': None,
            u'predicts': [{
                u'model_id': 1,
                u'model_params': {
                    u'maxnum_iter': 500,
                    u'save_freq': 50,
                    u'img_size': 32,
                    u'test_freq': 10,
                    u'layers': u'[data]\ntype=data\ndataidx=0\n[labels]\ntype=data\ndataidx=1\n[conv1]\ntype=conv\ninputs=data\nchannels=3\nfilters=32\npadding=2\nstride=1\nfiltersize=5\ninitw=0.0001\npartialsum=4\nsharedbiases=1\n[pool1]\ntype=pool\npool=max\ninputs=conv1\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\nneuron=relu\n[rnorm1]\ntype=rnorm\ninputs=pool1\nchannels=32\nsize=3\n[conv2]\ntype=conv\ninputs=rnorm1\nfilters=32\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool2]\ntype=pool\npool=avg\ninputs=conv2\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\n[rnorm2]\ntype=rnorm\ninputs=pool2\nchannels=32\nsize=3\n[conv3]\ntype=conv\ninputs=rnorm2\nfilters=64\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool3]\ntype=pool\npool=avg\ninputs=conv3\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=64\n[fc10]\ntype=fc\noutputs=10\ninputs=pool3\ninitw=0.01\n[probs]\ntype=softmax\ninputs=fc10\n[logprob]\ntype=cost.logreg\ninputs=labels,probs',
                    u'layer_params': u'[conv1]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\nnepsw=0.001\n[conv2]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[conv3]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[fc10]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=1\n[logprob]\ncoeff=1\n[rnorm1]\nscale=0.00005\npow=.75\n[rnorm2]\nscale=0.00005\npow=.75'
                },
                u'id': 1,
                u'out_nonlin': None,
                u'model_name': u'CONV',
                u's3_data': u'fixtures/modeldata/convnet_animals_250_iters.pkl'
            }],
            u'queue_key': u'583c6a09d52f59e2a64035d4464abcde68379162',
            u'options': {}
        }
        penguin = aws.S3Key('fixtures/images/penguin.jpg').get()
        ant = aws.S3Key('fixtures/images/ant.jpg').get()
        batch_data, _ = construct_predict_batch([penguin, ant])
        api_message['input_data'] = batch_data

        with fake_api(port=get_api_port(), default_response=json.dumps({'status': 'success'})) as calls:
            predict_convnet(api_message)
            self.assertEqual(calls[0].path, '/api/predict-ensemble/status/')
            data = json.loads(calls[0].body)
            penguin, ant = data['results']['img_labels']
            if ant['filename'] == 'penguin.jpg':
                penguin, ant = ant, penguin
            self.assertTrue('penguin' in [x[1] for x in penguin['labels']][:2])
            self.assertTrue('ant' in [x[1] for x in ant['labels']][:2])
