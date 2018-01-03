#-*- coding:utf-8 -*_

DEFAULTS = {
    'img_size': 32,
    'learning_rate': 0.01,
    'momentum': 0.9,
    'dropout': 0.5,
    'random_sparse': 'false',
    'layers': [
        {'type': 'convSet',
        'convChannels': 3,
        'convFilters': 32,
        'convPadding': 2,
        'convStride': 1,
        'convFilterSize': 5,
        'convSharedBiases': 1,
        'convDropout': 0.5,
        'poolStart': 0,
        'poolSizeX': 3,
        'poolStride': 2,
        'poolOutputsX': 0,
        'normSize': 3},
        {'type': 'convSet',
        'convChannels': 32,
        'convFilters': 32,
        'convPadding': 2,
        'convStride': 1,
        'convFilterSize': 5,
        'convSharedBiases': 1,
        'convDropout': 0.5,
        'poolStart': 0,
        'poolSizeX': 3,
        'poolStride': 2,
        'poolOutputsX': 0,
        'normSize': 3},
        {'type': 'convSet',
        'convChannels': 32,
        'convFilters': 32,
        'convPadding': 2,
        'convStride': 1,
        'convFilterSize': 5,
        'convSharedBiases': 1,
        'convDropout': 0.5,
        'poolStart': 0,
        'poolSizeX': 3,
        'poolStride': 2,
        'poolOutputsX': 0,
        'normSize': 10},
        {'type': 'fc',
        'outputs': 10}
    ]
}


def make_single_conv_block(blocknum, init_size,block_params,block_input=None,is_interior_layer=True):
    layers_template = ( 
        u'[conv{blocknum}]\n'
        'type=conv\n'
        'inputs={block_input}\n'
        'channels={convChannels}\n' #NOTE:new
        'filters={convFilters}\n' #NOTE:new
        'padding={convPadding}\n' #NOTE:new
        'stride={convStride}\n' #NOTE:new
        'filterSize={convFilterSize}\n' #NOTE:new
        'initW=0.0001\n'
        'partialSum=1\n'
        'sharedBiases={convSharedBiases}\n\n' #NOTE:new
        '[pool{blocknum}]\n'
        'type=pool\n'
        'pool=max\n'
        'inputs=conv{blocknum}\n'
        'start={poolStart}\n' #NOTE:new
        'sizeX={poolSizeX}\n' #NOTE: now user specified
        'stride={poolStride}\n' #NOTE: now user specified
        'outputsX=0\n'
        'channels=32\n' #Why isn't this pool channels parameter user specified like conv?
        'neuron=relu\n\n'
    )
    interior_only_layers = (
        '[rnorm{blocknum}]\n'
        'type=rnorm\n'
        'inputs=pool{blocknum}\n'
        'channels=32\n' #Why isn't this rnorm channels parameter user specified like conv?
        'size={normSize}\n\n' #NOTE: now user specified
    )
    params_template = (
        '[conv{blocknum}]\n'
        'epsW={{learning_rate}}\n'
        'epsB={{learning_rate}}\n'
        'momW={{momentum}}\n'
        'momB={{momentum}}\n'
        'wc=0.004\n'
        'dropout={{dropout}}\n'
        'randSparse={{random_sparse}}\n\n'
    )
    interior_only_params = (
        '[rnorm{blocknum}]\n'
        'scale=0.00005\n'
        'pow=.75\n\n'
    )
    # insert kludges here
    try:
        block_params['block_input'] = 'rnorm%s' % (blocknum-1) if blocknum else 'data'
    except:
        print block_params
    block_params['convChannels'] = block_params['convChannels'] if blocknum else 3
    block_params['normSize'] = min( block_params['normSize'], init_size / 2**(blocknum+1) )
    block_params['poolSizeX'] = min( block_params['poolSizeX'], init_size / 2**blocknum )
    block_params['poolStride'] = min( block_params['poolStride'], block_params['poolSizeX'] )
    if is_interior_layer:
        layers = layers_template + interior_only_layers
        params = params_template + interior_only_params
    else:
        layers = layers_template
        params = params_template
    block_params['blocknum'] = blocknum
    #layers_str += layers.format(blocknum).format(**kludges)
    layers_str = layers.format(**block_params)
    params_str = params.format(blocknum=blocknum)
    return (layers_str, params_str)


def make_conv_blocks(layerspecs, init_size, block_input=None):
    conv_layers_str = ""
    conv_params = ""
    num_layers = len(layerspecs)
    i = 0 # define in case loop doesn't run (num_layers !> 1)
    if num_layers > 1:
        for i, ls in enumerate(layerspecs[:-1]):
            cl, cp = make_single_conv_block(i, 
                        init_size, block_params=ls, is_interior_layer=True)
            conv_layers_str += cl
            conv_params += cp 
    num_layers -= 1
    i = max(i, num_layers)
    cl, cp = make_single_conv_block(num_layers, init_size, layerspecs[-1],
                is_interior_layer=False)
    conv_layers_str += cl
    conv_params += cp
    #conv_params_str = conv_params.format(**layerspecs) #redundant at the mo.
    return conv_layers_str, conv_params, i
        

def make_single_fc_block(blocknum, block_params, block_input=None):
    layers_template = (
        '[fc{blocknum}]\n'
        'type=fc\n'
        'outputs={{final_output}}\n'
        'inputs=pool{{conv_count}}\n'
        'initW=0.01\n\n'
    )
    params_template = (
        '[fc{blocknum}]\n'
        'epsW={{learning_rate}}\n'
        'epsB={{learning_rate}}\n'
        'momW={{momentum}}\n'
        'momB={{momentum}}\n'
        'wc=0.004\n'
        'dropout={{dropout}}\n'
        'randSparse={{random_sparse}}\n\n'
    )
    block_params['blocknum'] = blocknum
    layers_str = layers_template.format(**block_params)
    params_str = params_template.format(blocknum=blocknum)
    return (layers_str, params_str)


def make_fc_blocks(layerspecs, init_size, block_input=None, init_num=0):
    fc_layers_str = ""
    fc_params = ""
    num_layers = len(layerspecs)
    j = init_num + 1
    for i, ls in enumerate(layerspecs):
        fl, fp = make_single_fc_block(j, block_params=ls)
        fc_layers_str += fl
        fc_params += fp
        j += 1
    return fc_layers_str, fc_params, j-1
        

def make_cnn(wtf=None, **input_params):
    layers_template = (
        '[data]\n'
        'type=data\n'
        'dataIdx=0\n\n'
        '[labels]\n'
        'type=data\n'
        'dataIdx=1\n\n'
        '{conv_layers}\n\n'
        '{fc_layers}\n\n'
        '[probs]\n'
        'type=softmax\n'
        'inputs={{probs_input}}\n\n'
        '[logprob]\n'
        'type=cost.logreg\n'
        'inputs=labels,probs\n'
    )
    params_template = (
        '{conv_params}\n\n'
        '{fc_params}\n\n'
        '[logprob]\n'
        'coeff=1\n'
    )
    # I strongly suspect that this is messing things up and that defaults need to be moved
    # down to the individual layer level
    hparams = dict(DEFAULTS.items() + input_params.items())
    
    ### Conv Block Stuff ###
    conv_layer_specs = filter(lambda x: x['type'] == 'convSet', hparams['layers'])
    cl, cp, conv_count = make_conv_blocks(conv_layer_specs, init_size=hparams['img_size'])
    hparams['conv_count'] = conv_count #counter from make_conv_layers. maybe stopped early 

    ### FC Block Stuff ###
    fc_layer_specs = filter(lambda x: x['type'] == 'fc', hparams['layers'])
    fl, fp, j = make_fc_blocks(fc_layer_specs, init_size=hparams['img_size'], init_num=conv_count)
    if fc_layer_specs and conv_count<j:
        probs_input = "fc%s" % j
    else:
        probs_input = "pool%s" % conv_count
    hparams['probs_input'] = probs_input
    # wherever the new equivalent of conv_count is implemented, it needs to be a more
    # generalized layer_count that is incremented every time there's a layer subject to
    # "signal degradation"
    
    layers_str = layers_template.format(conv_layers=cl, fc_layers=fl).format(**hparams)
    params_str = params_template.format(conv_params=cp, fc_params=fp).format(**hparams)

    return layers_str, params_str


