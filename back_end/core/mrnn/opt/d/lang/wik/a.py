from pylab import load
print 'loading a GB of wikipedia...'
(data, _, _) = load('wiki_letters_500k_ppm')
print 'done.'    
_data = data
def wik(T, batch_size, T_warmup=50):
    test_frac = 5e6 / len(data)
    print 'test_frac is pretty small: %f' % test_frac
    from opt.d.lang import ContiguousText
    return ContiguousText('WIKI-1G', 
                          data,
                          T = T, 
                          batch_size = batch_size,
                          T_warmup = T_warmup,
                          train_prob = 1-test_frac)

def wik_perm(T, batch_size, T_warmup=50):
    from opt.d.lang import ContiguousText, permute_string
    data = permute_string('WIK-1G-PERM',
                          '\n\n',
                          _data)


    test_frac = 5e6 / len(data)
    print 'test_frac is pretty small: %f' % test_frac
    from opt.d.lang import ContiguousText
    return ContiguousText('WIKI-1G-PERM', 
                          data,
                          T = T, 
                          batch_size = batch_size,
                          T_warmup = T_warmup,
                          train_prob = 1-test_frac)


def wik_small_perm(T, batch_size, T_warmup=50):
    from opt.d.lang import ContiguousText, permute_string
    data = permute_string('WIK-1G-PERM',
                          '\n\n',
                          _data)
    # truncate
    data = data[-int(160e6):]

    test_frac = 5e6 / len(data)
    print 'test_frac is pretty small: %f' % test_frac
    from opt.d.lang import ContiguousText
    return ContiguousText('SMALL-WIKI-160M-PERM', 
                          data,
                          T = T, 
                          batch_size = batch_size,
                          T_warmup = T_warmup,
                          train_prob = 1-test_frac)





def shift_wik(T, batch_size, T_warmup=50):
    from opt.d.lang import ShiftCharContiguousText
    test_frac = 5e6 / len(data)
    return ShiftCharContiguousText('WIKI-1G', 
                                   data,
                                   T = T, 
                                   batch_size = batch_size,
                                   T_warmup = T_warmup,
                                   train_prob = 1 - test_frac)


