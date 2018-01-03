from pylab import load
print 'loading a GB of wikipedia...'
(data, _, _) = load('wiki_letters_500k_ppm')
data = data[:int(3e8)]
print 'done.'    

def small_wik(T, batch_size):
    test_frac = 5e6 / len(data)
    print 'test_frac is pretty small: %f' % test_frac
    from opt.d.lang import ContiguousText
    return ContiguousText('WIKI-300MB', 
                          data,
                          T, batch_size,
                          train_prob = 1-test_frac)


def shift_small_wik(T, batch_size):
    from opt.d.lang import ShiftCharContiguousText
    test_frac = 5e6 / len(data)
    return ShiftCharContiguousText('WIKI-300MB', 
                                   data,
                                   T, batch_size,
                                   train_prob = 1 - test_frac)


