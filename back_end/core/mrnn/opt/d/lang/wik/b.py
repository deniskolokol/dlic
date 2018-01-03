from pylab import load
print 'loading a GB of wikipedia...'
(data, _) = load('wiki_letters_2G')
_data = data
print 'done.'    

def wik(T, batch_size, T_warmup=50):
    test_frac = 10e6 / len(data)
    print 'test_frac is pretty small: %f' % test_frac
    from opt.d.lang import ContiguousText
    return ContiguousText('WIKI-1G', 
                          data,
                          T = T, 
                          batch_size = batch_size,
                          T_warmup = T_warmup,
                          train_prob = 1-test_frac)
