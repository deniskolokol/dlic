CONV = {u'maxnum_iter': 500,
        u'img_size': 32,
        u'layer_params': u'[conv1]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\nnepsw=0.001\n[conv2]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[conv3]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=0.004\n[fc10]\nepsw=0.001\nepsb=0.002\nmomw=0.9\nmomb=0.9\nwc=1\n[logprob]\ncoeff=1\n[rnorm1]\nscale=0.00005\npow=.75\n[rnorm2]\nscale=0.00005\npow=.75',
        u'layers': u'[data]\ntype=data\ndataidx=0\n[labels]\ntype=data\ndataidx=1\n[conv1]\ntype=conv\ninputs=data\nchannels=3\nfilters=32\npadding=2\nstride=1\nfiltersize=5\ninitw=0.0001\npartialsum=4\nsharedbiases=1\n[pool1]\ntype=pool\npool=max\ninputs=conv1\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\nneuron=relu\n[rnorm1]\ntype=rnorm\ninputs=pool1\nchannels=32\nsize=3\n[conv2]\ntype=conv\ninputs=rnorm1\nfilters=32\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool2]\ntype=pool\npool=avg\ninputs=conv2\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=32\n[rnorm2]\ntype=rnorm\ninputs=pool2\nchannels=32\nsize=3\n[conv3]\ntype=conv\ninputs=rnorm2\nfilters=64\npadding=2\nstride=1\nfiltersize=5\nchannels=32\nneuron=relu\ninitw=0.01\npartialsum=4\nsharedbiases=1\n[pool3]\ntype=pool\npool=avg\ninputs=conv3\nstart=0\nsizex=3\nstride=2\noutputsx=0\nchannels=64\n[fc10]\ntype=fc\noutputs=10\ninputs=pool3\ninitw=0.01\n[probs]\ntype=softmax\ninputs=fc10\n[logprob]\ntype=cost.logreg\ninputs=labels,probs',
        u'test_freq': 10,
        u'save_freq': 50}

#{u'T': 20,
 #u'cg_max_cg': 40,
 #u'cg_min_cg': 1,
 #u'f': 2,
 #u'h': 2,
 #u'lambda': 0.01,
 #u'maxnum_iter': 20,
 #u'mu': 0.001}
MRNN = {}

AUTOENCODER = {u'batch_size': 1000, u'maxnum_iter': 100,
               u'hidden_outputs': '20', u'regularization': 1.0,
               u'sparse_param': 0.0, u'sparse_weight': 1.0,
               u'noise_level': 0.0, u'opt_alg': u'L-BFGS'}

DEEPNET = {u'batch_size': 1000, u'maxnum_iter': 100,
           u'hidden_outputs': '20', u'regularization': 1.0,
           u'sparse_param': 0.0, u'sparse_weight': 1.0,
           u'noise_level': 0.0}

DEEPNET_SGD = {u'batch_size': 10, u'maxnum_iter': 100, u'max_momentum': .995,
               u'hidden_outputs': '10,10', u'l1_regularization': .0001,
               u'l2_regularization': .0001, u'dropout': False,
               u'learning_rate': .01, u'learning_rate_modifier': 0.9995}

