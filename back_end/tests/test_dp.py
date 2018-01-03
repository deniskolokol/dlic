import unittest
import pickle
from os import path
import numpy as np
from ersatz.mrnn import ersatz_dp as dp

CWD = path.dirname(path.abspath(__file__))


class TestLoadTimeSeries(unittest.TestCase):

    def setUp(self):
        self.datafile = path.join(CWD, 'fixtures/manualx.csv')
        with open(path.join(CWD, 'fixtures/manualx_out.pkl'), 'r') as f:
            self.out_data = pickle.load(f)
        self.quantiles = [
                (15.345999908447265, 16.553999883478337, 19.271999827298252),
                (0.0, 14.127272727272727, 197.78181818181818)]
        self.message_data = {'file_name': 'fixtures/manualx.zip',
                             'data_split': [60, 20, 20],
                             'quantiles': None, 'options': {'quantiles': True}}

    def test_dp_split(self):
        message_data = self.message_data.copy()
        message_data.update({'test_dataset': 'fixtures/manualx.zip',
                             'valid_dataset': 'fixtures/manualx.zip'})
        provider = dp.DP(message_data)
        provider.load_data()
        self.assertEqual(provider.len_output, 2)
        self.assertEqual(self.quantiles, provider.quantiles)
        shape = provider.data_shape
        self.assertTrue(0 < shape[0] < 32)
        self.assertTrue(shape[1] in [95, 96, 97])
        self.assertEqual(shape[2], 6)

    def test_dp_separate_test(self):
        message_data = self.message_data.copy()
        message_data.update({'test_dataset': 'fixtures/manualx.zip'})
        provider = dp.DP(message_data)
        provider.load_data()
        #train (26, {95, 96, 97}, 6)
        samples = sum(x.shape[0] for x in provider.binary_train_data)
        timesteps = {x.shape[1] for x in provider.binary_train_data}
        units = {x.shape[2] for x in provider.binary_train_data}
        self.assertEqual(samples, 26)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))
        #test (32, {95, 96, 97}, 6)
        samples = sum(x.shape[0] for x in provider.binary_test_data)
        timesteps = {x.shape[1] for x in provider.binary_test_data}
        units = {x.shape[2] for x in provider.binary_test_data}
        self.assertEqual(samples, 32)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))
        #valid (6, {95, 96, 97}, 6)
        samples = sum(x.shape[0] for x in provider.binary_valid_data)
        timesteps = {x.shape[1] for x in provider.binary_valid_data}
        units = {x.shape[2] for x in provider.binary_valid_data}
        self.assertEqual(samples, 6)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))

    def test_dp_separate_files(self):
        message_data = self.message_data.copy()
        message_data.update({'test_dataset': 'fixtures/manualx.zip',
                             'valid_dataset': 'fixtures/manualx.zip'})
        provider = dp.DP(message_data)
        provider.load_data()
        #train (32, {95, 96, 97}, 6)
        self.assertEqual(len(provider.binary_train_data), 3)
        samples = sum(x.shape[0] for x in provider.binary_train_data)
        timesteps = {x.shape[1] for x in provider.binary_train_data}
        units = {x.shape[2] for x in provider.binary_train_data}
        self.assertEqual(samples, 32)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))
        #test (32, {95, 96, 97}, 6)
        self.assertEqual(len(provider.binary_test_data), 3)
        samples = sum(x.shape[0] for x in provider.binary_test_data)
        timesteps = {x.shape[1] for x in provider.binary_test_data}
        units = {x.shape[2] for x in provider.binary_test_data}
        self.assertEqual(samples, 32)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))
        #valid (32, {95, 96, 97}, 6)
        self.assertEqual(len(provider.binary_valid_data), 3)
        samples = sum(x.shape[0] for x in provider.binary_valid_data)
        timesteps = {x.shape[1] for x in provider.binary_valid_data}
        units = {x.shape[2] for x in provider.binary_valid_data}
        self.assertEqual(samples, 32)
        self.assertTrue(all(x in [95, 96, 97] for x in timesteps))
        self.assertEqual(units, set([6]))


class TestDynamicBatches(unittest.TestCase):

    def test_timestep_split(self):
        timestep = "1,2,3,4|1,0"
        len_input, len_output, splitter = dp.get_timestep_split(timestep)
        self.assertEqual(len_input, 4)
        self.assertEqual(len_output, 2)
        inp, out = splitter(timestep, 'fake')
        self.assertEqual(inp, ['1', '2', '3', '4'])
        self.assertEqual(out, ['1', '0'])

    def test_timestep_split_0_out(self):
        timestep = "1,2,3,4,1,0"
        len_input, len_output, splitter = dp.get_timestep_split(timestep)
        self.assertEqual(len_input, 6)
        self.assertEqual(len_output, 0)
        inp, out = splitter(timestep, 'fake')
        self.assertEqual(inp, ['1', '2', '3', '4', '1', '0'])
        self.assertEqual(out, [])

    def test_sample_preprocess(self):
        sample = ["1,2,3,4|0,1", "2,3,4,5|1,0", " 2,2,2,2|0, 0"]

        len_input, len_output, splitter = dp.get_timestep_split(sample[0])
        psample = dp.sample_preprocess(sample, len_output, len_input, splitter, True)
        self.assertEqual(psample, [['1', '2', '3', '4', '0', '1'],
                                   ['2', '3', '4', '5', '1', '0'],
                                   [' 2', '2', '2', '2', '0', ' 0']])

    def test_sample_preprocess_binarize(self):
        sample = ["1,2,3|0,1", "2,3,4|1,0"]

        len_input, len_output, splitter = dp.get_timestep_split(sample[0])
        psample = dp.sample_preprocess(sample, len_output, len_input, splitter, False)
        self.assertEqual(psample, [['1', 0, '2', 0, '3', 0, '0', '1'],
                                   ['2', 0, '3', 0, '4', 0, '1', '0']])

    def test_strip_split_samples(self):
        lines = ["1,2,3,4|0,1;2,3,4,5|1,0; 2,2,2,2|0, 0;", "1, 2, 3|0, 0;"]
        data = dp.strip_split_samples(lines)
        self.assertEqual([["1,2,3,4|0,1", "2,3,4,5|1,0", " 2,2,2,2|0, 0"],
                          ["1, 2, 3|0, 0"]], data)

    def test_construct_batches(self):
        lines = ["1,2,3,4|0,1;2,3,4,5|1,0; 2,2,2,2|0, 0;",
                 "1, 2, 3, 0|0, 0;",
                 "1,2,3,4|0,1;2,3,4,5|1,0; 2,2,2,1|0, 0;",
                 "1, 2, 3, 0|0, 0;",
                 "2,3,4,5|1,1;2,2,3,4|0,0;"]
        data = dp.strip_split_samples(lines)
        len_input, len_output, splitter = dp.get_timestep_split(data[0][0])
        batches, original_order = dp.construct_batches(data, len_output,
                                                       len_input, splitter, True)
        order = (0, 2, 4, 1, 3)
        # 2 samples with 3 timesteps each
        batch0 = np.array([[[1.0, 2.0, 3.0, 4.0, 0.0, 1.0],
                            [2.0, 3.0, 4.0, 5.0, 1.0, 0.0],
                            [2.0, 2.0, 2.0, 2.0, 0.0, 0.0]],
                           [[1.0, 2.0, 3.0, 4.0, 0.0, 1.0],
                            [2.0, 3.0, 4.0, 5.0, 1.0, 0.0],
                            [2.0, 2.0, 2.0, 1.0, 0.0, 0.0]]])
        # 1 sample with 2 timesteps each
        batch1 = np.array([[[2.0, 3.0, 4.0, 5.0, 1.0, 1.0],
                            [2.0, 2.0, 3.0, 4.0, 0.0, 0.0]]])
        # 2 samples with 1 timestep each
        batch2 = np.array([[[1.0, 2.0, 3.0, 0.0, 0.0, 0.0]],
                           [[1.0, 2.0, 3.0, 0.0, 0.0, 0.0]]])
        self.assertEqual(order, original_order)
        self.assertTrue((batch0 == batches[0]).any())
        self.assertTrue((batch1 == batches[1]).any())
        self.assertTrue((batch2 == batches[2]).any())

    def test_get_quantiles(self):
        # even column equals 0, because we will replace values with
        # binary values
        batches =[np.array([[[1.0, .0, 3.0, .0, 0.0, 1.0],
                             [2.0, .0, 4.0, .0, 1.0, 0.0],
                             [2.0, .0, 2.0, .0, 0.0, 0.0]],
                            [[1.0, .0, 3.0, .0, 0.0, 1.0],
                             [2.0, .0, 4.0, .0, 1.0, 0.0],
                             [2.0, .0, 2.0, .0, 0.0, 0.0]]]),
                  np.array([[[2.0, .0, 4.0, .0, 1.0, 1.0],
                             [2.0, .0, 3.0, .0, 0.0, 0.0]]]),
                  np.array([[[1.0, .0, 3.0, .0, 0.0, 0.0]],
                            [[1.0, .0, 3.0, .0, 0.0, 0.0]]])]
        quantiles = dp.calculate_quantiles(batches, len_output=2)
        column1 = np.array([1.0, 2.0, 2.0, 1.0, 2.0, 2.0, 2.0, 2.0, 1.0, 1.0,])
        column2 = np.array([3.0, 4.0, 2.0, 3.0, 4.0, 2.0, 4.0, 3.0, 3.0, 3.0,])
        qntl = [(dp.quantile(column1, .25),
                 dp.quantile(column1, .50),
                 dp.quantile(column1, .75))]
        qntl.append((dp.quantile(column2, .25),
                     dp.quantile(column2, .50),
                     dp.quantile(column2, .75)))
        self.assertEqual(quantiles, qntl)


    def test_datafile(self):
        fp = dp.get_data('fixtures/manualx.zip')
        lines = dp.open_datafile(fp)
        data = dp.strip_split_samples(lines)
        len_input, len_output, splitter = dp.get_timestep_split(data[0][0])
        batches, original_order = dp.construct_batches(data, len_output,
                                                       len_input, splitter, True)
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0].shape[2], 4)
        self.assertEqual(batches[0].shape[1], 97)
        self.assertEqual(batches[1].shape[1], 96)
        self.assertEqual(batches[2].shape[1], 95)
        self.assertEqual(sum(batches[x].shape[0] for x in range(len(batches))), 32)

    def test_datafile_bin(self):
        fp = dp.get_data('fixtures/manualx.zip')
        lines = dp.open_datafile(fp)
        data = dp.strip_split_samples(lines)
        len_input, len_output, splitter = dp.get_timestep_split(data[0][0])
        batches, original_order = dp.construct_batches(data, len_output,
                                                       len_input, splitter, False)
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0].shape[2], 6)
        self.assertEqual(batches[0].shape[1], 97)
        self.assertEqual(batches[1].shape[1], 96)
        self.assertEqual(batches[2].shape[1], 95)
        self.assertEqual(sum(batches[x].shape[0] for x in range(len(batches))), 32)

if __name__ == '__main__':
    unittest.main()
