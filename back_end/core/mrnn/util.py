import os
import ctypes
import numpy as np
from numpy import random
from math import ceil, floor
from scipy.stats import scoreatpercentile
from ..exception import ApiParamsError


_ctypes_to_numpy = {
    ctypes.c_char : np.int8,
    ctypes.c_wchar : np.int16,
    ctypes.c_byte : np.int8,
    ctypes.c_ubyte : np.uint8,
    ctypes.c_short : np.int16,
    ctypes.c_ushort : np.uint16,
    ctypes.c_int : np.int32,
    ctypes.c_uint : np.int32,
    ctypes.c_long : np.int32,
    ctypes.c_ulong : np.int32,
    ctypes.c_float : np.float32,
    ctypes.c_double : np.float64
}


def shmem_as_ndarray(array_or_value):
    """ view processing.Array or processing.Value as ndarray """
    obj = array_or_value._obj
    buf = obj._wrapper._state[0][0].buffer
    try:
         t = _ctypes_to_numpy[type(obj)]
         return np.frombuffer(buf, dtype=t, count=1)
    except KeyError:
        t = _ctypes_to_numpy[obj._type_]
        return np.frombuffer(buf, dtype=t)


def shmem_as_ndarray2(raw_array, shape=None):

    address = raw_array._obj._wrapper.get_address()
    size = len(raw_array)
    if (shape is None) or (np.asarray(shape).prod() != size):
        shape = (size,)
    elif type(shape) is int:
        shape = (shape,)
    else:
        shape = tuple(shape)

    dtype = _ctypes_to_numpy[raw_array._obj._type_]
    class Dummy(object): pass
    d = Dummy()
    d.__array_interface__ = {
        'data' : (address, False),
        'typestr' : np.dtype(dtype).str,
        'descr' : np.dtype(dtype).descr,
        'shape' : shape,
        'strides' : None,
        'version' : 3
    }
    return np.asarray(d).view(dtype=dtype)


def to_masked_array_of_different_len(lst):
    if not lst:
        return lst
    num = len(lst)
    shapes = [x.shape for x in lst]
    shape = [max(shape) for shape in zip(*shapes)]
    shape = [num] + shape
    arr = np.ma.empty(shape)
    arr.mask = True
    if len(shape) == 2:
        for i, entry in enumerate(lst):
            arr[i, :entry.shape[0]] = entry
    elif len(shape) == 3:
        for i, entry in enumerate(lst):
            arr[i, :entry.shape[0], :entry.shape[1]] = entry
    return arr


def cpu(x):
    try:
        return x.asarray()
    except:
        return x


def mcpu(x):
    return map(cpu, x)


def to_gpu(x):
    import gnumpy as g
    return g.garray(x)


def partition_batches(L, i, tot):
    if len(L) == 1:
        assert i == 0 and tot == 1
        return L

    print "i=%d\ttot=%d\tlen(L)=%d" % (i, tot, len(L))
    assert 0 <= i < tot and len(L) >= tot;

    l = len(L) - 1
    part_size = int(np.ceil(float(l)/float(tot)))
    return L[i * part_size:(i + 1) * part_size + (i + 1 == tot) * part_size]


def grab_gpu_boards():
    boards = os.environ.get('ERSATZ_MRNN_GPUS', '0')
    return [int(x) for x in boards.split(',')]


def calculate_batch_size(dataset_size, max_batch_size, min_batches):
    """
    we need to select maximum possible batch size
    """
    if dataset_size < min_batches:
        # in this case we can't create minimum number of batches
        # even with one sample in batch
        raise ApiParamsError('Train or test dataset is too small',
                             show_to_user=True)
    num_batches = int(ceil(dataset_size / float(max_batch_size)))
    batch_size = max_batch_size
    if num_batches < min_batches:
        batch_size = int(floor(dataset_size / min_batches))
        num_batches = int(ceil(dataset_size / float(batch_size)))
    return batch_size, num_batches


def generate_fake_data(T_steps, N_dimensions, N_samples):
    data = []
    for sample in xrange(N_samples):
        sequence = []
        for t in xrange(T_steps):
            sample = [random.uniform(-1,1) for n in xrange(N_dimensions)]
            # the last number for each sample represents
            # tomorrow's results (and the objective).  
            # If the final value (change in price)
            # > .02, then it's 1, otherwise it's 0
            # This will fail on the first one, because there is no data
            # on the following day (typically, this is the day you want
            # to predict.
            try:
                if sequence[-1][-1] > .02:
                    sample.append(1.)
                else:
                    sample.append(0.)
            except:
                pass
            sequence.append(sample)
        data.append(sequence)
    # At this point, your sequences are in order going
    # from newest to oldest. When it goes into the network,
    # you want it to be oldest to newest.  So reverse each sequence.
    [d.reverse() for d in data]
    return data

def binarize(data_list, percentile_scores, single_sequence=False):
    """ A rather inflexible function to take a list of time series with
        values between -1 and 1 and convert them to a 2-bit binary representation
        of 'sign'+'magnitude' where magnitude is related to the percentiles
        of that given column, percentiles being supplied in a list and having
        been pre-computed separately

        'single_sequence' is a convoluted attempt to deal with the make_predictions
        script, which supplies its 'data_list' as a single time sequence,
        rather than a list of time sequences """

    def spit_bit(point,percentile_score1,percentile_score2):
        """ given a real numbered datapoint and percentile cut offs
            (score1=80th percentile off, score2=20th percentile cutoff),
            return a 2-bit binary data point """
        if point > 0.:
            if point>percentile_score1:
                return [1.,1.]
            else:
                return [1.,0.]
        else:
            if point<percentile_score2:
                return [0.,1.]
            else:
                return [0.,0.]


    if single_sequence:
        new_sequence = []
        #if len(data_list) > 0:
            #target_length = len(data_list[1])-5
        #else:
            #target_length = 7
        for sample in xrange(len(data_list)):
            new_t = []
            pointer = 0
            #if sample == len(data_list)-1 and len(data_list[sample][1:])==target_length:
            iterator = data_list[sample][1:]
            #else:
            #   iterator = data_list[sample][1:-4]
            for point in iterator:
                try:
                    new_t.extend(spit_bit(point, percentile_scores[pointer], percentile_scores[pointer+1]))
                except:
                    print 'error normalizing-check your shapes son...'
                    continue
                pointer+=2
                if pointer == len(percentile_scores):
                    break
            #if sample != len(data_list)-1:
            new_t.extend(data_list[sample][-4:])
            data_list[sample] = new_t
        return data_list

    for sequence_counter in xrange(len(data_list)):
        new_sequence = []
        for t in data_list[sequence_counter]:
            new_t = []
            pointer = 0
            for point in t[:-4]:
                new_t.extend(spit_bit(point, percentile_scores[pointer], percentile_scores[pointer+1]))
                pointer += 2
            new_t.extend(t[-4:])
            new_sequence.append(new_t)
        data_list[sequence_counter] = new_sequence

    return data_list

def generate_percentiles(data_list, simulation=False):

    percentile_scores = []
    column_values = []
    if not simulation:
       columns = len(data_list[1][1])-4
       loop = range(columns)
    else:
       # handle case of make_predictions
       columns = len(data_list[1][1:])+1
       loop = range(1, columns)


    for iteration in loop:
        column_values = []
        if not simulation:
            _ = [[column_values.append(sample[iteration]) for sample in sequence] for sequence in data_list]
            del _
        else:
            try:
                _ = [column_values.append(sample[iteration]) for sample in data_list]
                del _
            except:
                continue
        #print 'scoring at percentile for column %i/%i' % (iteration+1, columns)
        percentile_scores.append(scoreatpercentile(column_values, 80))
        percentile_scores.append(scoreatpercentile(column_values, 20))

    return percentile_scores

def save_prices(prices, save_path):
    import cPickle

    save = open(save_path, 'wb')
    cPickle.dump(prices, save, protocol=2)
    save.close()

#SECURITY_LIST = 'data_prep/russel_3000.csv'
#META_DATA_DIR = 'data'
#MAX_STOCKS_TO_DOWNLOAD = 2950
#SAVE_STOCK_DATA_AS = 'r3000_12_5_12.pickle'
def load_securities(SECURITY_LIST, MAX_STOCKS_TO_DOWNLOAD, META_DATA_DIR):
    """ download all the securities listed in the file SECURITY_LIST, also download metadata 
        return a pricing dictionary with the ticker symbol price history, but does not do so
        for the metadata--it simply downloads the metadata and MetaProvider later stripes it in.

        Might be a good idea to put all the metadata stuff into MetaProvider...
    """
    import os
    import re
    import pycurl
    import time
    from StringIO import StringIO
    from termcolor import colored
    from dateutil import parser

    print 'refreshing metadata from directory %s' % colored(META_DATA_DIR, 'red')

    meta_data_files = os.listdir(META_DATA_DIR)

    success = False
    for filename in meta_data_files:
        with open(META_DATA_DIR+'/'+filename) as f:
            for x in range(2):
                f.next()
            update_url = re.search('http://.*(?=\\n)', f.next()).group()

            print 'fetch: %s' % update_url
            storage = StringIO()
            headers = StringIO()
            c = pycurl.Curl()
            c.setopt(c.URL, update_url)
            c.setopt(c.WRITEFUNCTION, storage.write)
            c.setopt(c.HEADERFUNCTION, headers.write)
            try:
                c.perform()
                c.close()
            except:
                print 'Empty response recieved... skipping'
                time.sleep(5)
                continue
            r = storage.getvalue()
            headers = headers.getvalue()
            if re.search('200 OK', headers)==None:
                print 'other error getting metadata'
                continue
            success = True
            time.sleep(1)
        if success:
            f = open(META_DATA_DIR+'/'+filename, 'wb')
            for l in r.split('\n')[:-1]:
                f.write(l+'\n')
            f.close()

    print '\n\nMoving to stocks now\n\n'

    pricing = {}
    with open(SECURITY_LIST) as f:

        counter = 0
        for security in f:
            if counter==MAX_STOCKS_TO_DOWNLOAD:
                break
            else:
                counter+=1
            security = security.strip()
            pricing[security] = []
            print 'fetch %s %i/%i' % (security, counter, MAX_STOCKS_TO_DOWNLOAD)
            storage = StringIO()
            headers = StringIO()
            c = pycurl.Curl()
            c.setopt(c.URL, 'http://ichart.finance.yahoo.com/table.csv?s='+security.replace('$','')+'&a=08&b=7&c=1984&d=08&e=2&f=2013&g=d&ignore=.csv')
            c.setopt(c.WRITEFUNCTION, storage.write)
            c.setopt(c.HEADERFUNCTION, headers.write)
            try:
                c.perform()
                c.close()
            except:
                print 'Empty response recieved... skipping'
                time.sleep(5)
                continue
            r = storage.getvalue()
            headers = headers.getvalue()
            if re.search('200 OK', headers)==None:
                print '%s isnt a valid ticker--skipping...' % (security,)
                continue
            time.sleep(1)
            
            counter_2 = 0
            for line in r.split('\n')[:-1]:
                if counter_2 < 1:
                    counter_2+= 1
                    continue
                else:
                    counter_2+= 1
                p = line.split(',')
                try:
                    pricing[security].append( [parser.parse(p[0]).date(), float(p[5]), float(p[3]), float(p[2]), float(p[4]), float(p[1])] )
                    #date, volume, low, high, close, open
                    #pricing[security].append(  [ parser.parse(p[0]).date(), float(p[6]), float(p[5]), float(p[1]), float(p[2]), float(p[3]), float(p[4]) ]  )
                except:
                    print 'error adding information for %s' % (security,)
                    continue

    return pricing 
