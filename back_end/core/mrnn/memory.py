import os
import sys
from .util import grab_gpu_boards
from .pynvml import (nvmlInit, nvmlDeviceGetHandleByIndex,
                     nvmlDeviceGetMemoryInfo)


def get_free_memory():
    """
    returns free host memory in bytes
    """

    if sys.platform == 'win32':
        raise NotImplementedError('Not implemented for windows')
    elif sys.platform == 'darwin':
        raise NotImplementedError('Not implemented for mac')
    elif 'linux' in sys.platform:
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemFree'):
                        try:
                            mem = int(line.split()[1]) * 1024
                        except ValueError:
                            break
                        return mem
        except IOError:
            pass
        raise NotImplemented('Not implemented for this linux distro')
    raise NotImplemented('Not implemented for this OS')


def get_gpu_free_memory(gpu_id):
    """
    returns free GPU<gpu_id> memory in bytes
    """

    nvmlInit()
    handle = nvmlDeviceGetHandleByIndex(gpu_id)
    return nvmlDeviceGetMemoryInfo(handle).free


def get_size_of_mrnn(v, o, h, f, T):
    """
    calculate size of the network
    """

    T += 1  # for bias
    constant_size = 0
    sample_size = 0
    h_init = h       # h_init
    W_hf = h * f   # W_hf
    W_fh = f * h   # W_fh
    f_bias = f       # f_bias
    W_vh = v * h   # W_vh
    W_vf = v * f   # W_vf
    W_ho = h * o   # W_ho
    constant_size += h_init + W_hf + W_fh + f_bias + W_vh + W_vf + W_ho
    O = T * o   # output
    V = T * v   # input
    sample_size += O + V

    #forward_pass
    A = T * f
    B = T * f
    H = T * h
    C_t = W_fh
    AB = f
    HX_t = h
    OX = o
    new_w_ho = W_ho  # mask?
    constant_size += new_w_ho
    sample_size += A + B + H + C_t + AB + HX_t + OX
    return constant_size * 4 * 2, sample_size * 4 * 2


def get_max_gnumpy_memory():
    """
    returns memory size available for gnumpy
    if worker use GPU then gpu memory returns else host memory
    we use only 60% of free memory because higher values
    not safe (GPU memory error possible, 60% selected by experiment)
    """

    if os.environ.get('GNUMPY_USE_GPU', 'yes') == 'yes':  # run on gpu
        gpu_memory = min(get_gpu_free_memory(gpu_id)
                         for gpu_id in grab_gpu_boards())
    else:
        gpu_memory = get_free_memory()
    return gpu_memory * 0.6


def get_batch_size(v, o, h, f, T):
    """
    returns max possible batch size for network params
    and max memory for gnumpy max_memory_usage parameter
    """
    gpu_memory = get_max_gnumpy_memory()
    constant, per_sample = get_size_of_mrnn(v, o, h, f, T)
    batch_size = int((gpu_memory - constant) / per_sample)
    return batch_size, gpu_memory
