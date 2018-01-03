import json
import unittest
from fake_api import default_fake_api
from mocks import upload_modeldata_mock
from ersatz.pylearn.runners import TrainRunner

# TODO: add test for confusion matrix, now if train set doesn't contain
# one class which test set contain, keyerror raised


class TestAutoencoder(unittest.TestCase):
    def test_train(self):
        api_message = {
            u'data_type': u'GENERAL',
            u'models': [{
                u'model_params': {
                    u'maxnum_iter': 10,
                    u'save_freq': 5,
                    u'hidden_outputs': 500,
                    u'noise_level': 0.2,
                    u'learning_rate': {u'init': 0.001},
                    u'batch_size': 128,
                    u'irange': 0.05
                },
                u'out_nonlin': u'',
                u'id': 2,
                u'name': u'AUTOENCODER'
            }],
            u'file_name': u'fixtures/mnist/train_in.csv.zip',
            u'data_split': [100, 0, 0],
            u'sp_results': u'',
            u'options': None,
            u'quantiles': None,
            u'config': None,
            u'queue_key': u'e3e3ef0fb23c8e97d279d07cdca8ebf3eff7d303',
            u'ensemble': 1
        }
        runner = TrainRunner(api_message)
        with default_fake_api() as calls:
            with upload_modeldata_mock():
                runner.train_models()
                self.assertEqual(len(calls), 12)
                self.assertEqual(json.loads(calls[0].body)['state'], u'TRAIN')
                self.assertEqual(json.loads(calls[-1].body)['state'], u'FINISHED')
                self.assertEqual(json.loads(calls[-2].body)['data']['iteration'], 9)
                train_outputs = json.loads(calls[-2].body)['data']['train_outputs']
                self.assertEqual(len(train_outputs), 10)
                iteration, cost = train_outputs[0]
                self.assertEqual(iteration, 0)
                self.assertTrue(cost > 25)
                iteration, cost = train_outputs[-1]
                self.assertEqual(iteration, 9)
                self.assertTrue(cost < 15)


if __name__ == '__main__':
    unittest.main()
