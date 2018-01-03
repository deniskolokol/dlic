import unittest
from ersatz.mrnn import cnn_maker4 as cm

api_msg = {u'maxnum_iter': 100,
           u'img_size': 32,
           u'random_sparse': False,
           u'save_freq': 20,
           u'test_freq': 10,
           u'dropout': 0.1,
           u'learning_rate': 0.01,
           u'momentum': 0.5,
           u'layers': [
                       {u'type': u'convSet',
                       u'layer_name': u'h0',
                       u'convChannels': 3,
                       u'convFilters': 32,
                       u'convPadding': 2,
                       u'convStride': 1,
                       u'convFilterSize': 5,
                       u'convSharedBiases': 1,
                       u'convDropout': 0.5,
                       u'poolStart': 0,
                       u'poolSizeX': 3,
                       u'poolStride': 2,
                       u'poolOutputsX': 0,
                       u'normSize': 10},

                       {u'type': u'fc',
                       u'layer_name': u'h1',
                       u'hiddenUnits': 10}]}

def where_the_fuck(a,b,context=20):
    """debugging helper function that prints the characters immediately preceding and
    immediately proceeding the first mismatched character between two strings.
    """
    fucking_length = min(len(a),len(b))
    for i in xrange(fucking_length):
        if a[i] != b[i]:
            print (a[i-(context/2):i+(context/2)], b[i-(context/2):i+(context/2)])
            raise Exception()
    print "Perfect Match. Length mismatch"
    print len(a)
    print len(b)
    raise Exception()


class TestMakeSingleConvBlock(unittest.TestCase):
    def test_interior_layer(self):
        layer_params =  {u'type': u'convSet',
                        u'layer_name': u'h0',
                        u'convChannels': 3,
                        u'convFilters': 32,
                        u'convPadding': 2,
                        u'convStride': 1,
                        u'convFilterSize': 5,
                        u'convSharedBiases': 1,
                        u'convDropout': 0.5,
                        u'poolStart': 0,
                        u'poolSizeX': 3,
                        u'poolStride': 2,
                        u'poolOutputsX': 0,
                        u'normSize': 3}
        expected_layers = "[conv0]\ntype=conv\ninputs=data\nchannels=3\nfilters=32\npadding=2\nstride=1\nfilterSize=5\ninitW=0.0001\npartialSum=1\nsharedBiases=1\n\n[pool0]\ntype=pool\npool=max\ninputs=conv0\nstart=0\nsizeX=3\nstride=2\noutputsX=0\nchannels=32\nneuron=relu\n\n[rnorm0]\ntype=rnorm\ninputs=pool0\nchannels=32\nsize=3\n\n"
        expected_params = "[conv0]\nepsW={global_learning_rate}\nepsB={global_learning_rate}\nmomW={global_momentum}\nmomB={global_momentum}\nwc=0.004\ndropout={dropout}\nrandSparse={random_sparse}\n\n[rnorm0]\nscale=0.00005\npow=.75\n\n"
        layers_str, params_str = cm.make_single_conv_block(0, 32, layer_params)
        try:
            self.assertEqual(layers_str, expected_layers)
        except:
            where_the_fuck(layers_str, expected_layers)
        try:
            self.assertEqual(params_str, expected_params)
        except:
            where_the_fuck(params_str, expected_params)
        
    def test_non_interior_layer(self):
        layer_params =  {u'type': u'convSet',
                        u'layer_name': u'h0',
                        u'convChannels': 3,
                        u'convFilters': 32,
                        u'convPadding': 2,
                        u'convStride': 1,
                        u'convFilterSize': 5,
                        u'convSharedBiases': 1,
                        u'convDropout': 0.5,
                        u'poolStart': 0,
                        u'poolSizeX': 3,
                        u'poolStride': 2,
                        u'poolOutputsX': 0,
                        u'normSize': 3}
        expected_layers = "[conv0]\ntype=conv\ninputs=data\nchannels=3\nfilters=32\npadding=2\nstride=1\nfilterSize=5\ninitW=0.0001\npartialSum=1\nsharedBiases=1\n\n[pool0]\ntype=pool\npool=max\ninputs=conv0\nstart=0\nsizeX=3\nstride=2\noutputsX=0\nchannels=32\nneuron=relu\n\n"
        expected_params = "[conv0]\nepsW={global_learning_rate}\nepsB={global_learning_rate}\nmomW={global_momentum}\nmomB={global_momentum}\nwc=0.004\ndropout={dropout}\nrandSparse={random_sparse}\n\n"
        layers_str, params_str = cm.make_single_conv_block(0, 32, layer_params, is_interior_layer=False)
        try:
            self.assertEqual(layers_str, expected_layers)
        except:
            where_the_fuck(layers_str, expected_layers)
        try:
            self.assertEqual(params_str, expected_params)
        except:
            where_the_fuck(params_str, expected_params)

    def test_kludge(self):
        pass
    def test_non_0th_layer_blockinput(self):
        pass

class TestMakeSingleFCBlock(unittest.TestCase):
    def test_all_valid(self):
        pass
    def test_all_invalid(self):
        pass

class TestMakeConvBlocks(unittest.TestCase):
    def test_single_block(self):
        pass
    def test_multi_block(self):
        pass

class TestMakeFCBlocks(unittest.TestCase):
    def test_single_block(self):
        pass
    def test_multi_block(self):
        pass

class TestMakeCNN(unittest.TestCase):
    def test_old_default(self):
        pass
    def test_no_fc(self):
        pass
    def test_no_conv(self):
        pass
    def test_null_input(self):
        pass

