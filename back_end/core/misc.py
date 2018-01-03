import os
import sys
import json
import hashlib
import cStringIO
import gzip
import argparse
import numpy as np
from termcolor import colored
from mrnn.pynvml import (nvmlInit, nvmlDeviceGetHandleByIndex,
                         nvmlDeviceGetName, nvmlDeviceGetMemoryInfo,
                         NVMLError)


class NPArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.int, np.float32, np.float64)):
            return np.asscalar(obj)
        from .mrnn import gnumpy as g
        if isinstance(obj, g.garray):
            return obj.as_numpy_array().tolist()
        return json.JSONEncoder.default(self, obj)


def gzip_to_str(out):
    if not isinstance(out, file):
      out = cStringIO.StringIO(out)

    f = gzip.GzipFile(fileobj=out, mode='rb')
    data = f.read()
    f.close()
    return data


def str_to_gzip(data):
    out = cStringIO.StringIO()
    f = gzip.GzipFile(fileobj=out, mode='wb')
    f.write(data)
    f.close()
    return out.getvalue()


def fp_md5(file_, blocksize=65536):
    with open(file_) as f:
        hasher = hashlib.md5()
        buf = f.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(blocksize)
        return hasher.hexdigest()


def set_gpu_from_args():
    def print_gpu_info(gid):
        try:
            handle = nvmlDeviceGetHandleByIndex(gid)
        except NVMLError:
            print colored('Gpu with id %s doesn\'t exist' % gid, 'red')
            exit(1)
        device = nvmlDeviceGetName(handle)
        info = nvmlDeviceGetMemoryInfo(handle)
        msg = '\tGPU %s: %s, Memory used/total: %s/%s MB' % (gid, device,
                                                             int(info.used/1024/1024),
                                                             int(info.total/1024/1024))
        print colored(msg, 'green')

    def config_gpu(args):
        gpu = str(args.gpu)
        print 'For all jobs using gpu: %s' % gpu
        nvmlInit()
        print_gpu_info(args.gpu)
        if args.mgpu is None:
            mgpu = str(gpu)
        else:
            if len(set(args.mgpu)) != len(args.mgpu):
                print colored('Not unique ids for mrnn gpus.', 'red')
                exit(1)
            mgpu = ','.join(str(x) for x in args.mgpu)
            print 'For mrnn using %s gpus with ids: %s' % (len(args.mgpu), mgpu)
            for gid in args.mgpu:
                print_gpu_info(gid)

        os.environ['GNUMPY_USE_GPU'] = 'yes'
        os.environ['ERSATZ_GPU_ID'] = gpu
        os.environ['ERSATZ_MRNN_GPUS'] = mgpu
        os.environ['THEANO_FLAGS'] = 'mode=FAST_RUN,device=gpu' + gpu + ',floatX=float32'

    def config_cpu(args):
        if args.mcpus is None:
            mcpus = '0'
        else:
            mcpus = ','.join(str(x) for x in range(args.mcpus))
        os.environ['GNUMPY_USE_GPU'] = 'no'
        os.environ['ERSATZ_MRNN_GPUS'] = mcpus
        os.environ['THEANO_FLAGS'] = 'mode=FAST_RUN,device=cpu,floatX=float32'

    parser = argparse.ArgumentParser()
    group = parser.add_argument_group('cpu', 'options to run on cpu')
    group.add_argument('--cpu', action='store_true',
                        help="run all jobs on CPU")
    group.add_argument('--mcpus', type=int, default=1,
                        help=("numer of cpu to use for mrnn. CPU mode only "
                              "(default: 1)"))
    group = parser.add_argument_group('gpu', 'options to run on gpu')
    group.add_argument('--gpu', type=int, default=0,
                        help="which GPU to use for running jobs (default: 0)")
    group.add_argument('--mgpu', type=int, action='append',
                        help=("which gpus to use for mrnn training, "
                              "if not specified then it will run on one gpu "
                              "with id from --gpu or 0."
                              "(example: --mgpu 0 --mgpu 2. This will run mrnn "
                              "on two gpus with id 0 and 2)"))
    args = parser.parse_args()
    if args.cpu:
        if args.mgpu is not None:
            parser.error('do not use --mgpu with --cpu, use --mcpus instead')
        print colored('************ STARTED ON CPU ************', 'red')
        config_cpu(args)
    else:
        if any(x is not None for x in (args.cpu, args.mcpus)):
            pass
        config_gpu(args)


def scale_to_unit_interval(ndar, eps=1e-8):
    """ Scales all values in the ndarray ndar to be between 0 and 1 """
    ndar = ndar.copy()
    ndar -= ndar.min()
    ndar *= 1.0 / (ndar.max() + eps)
    return ndar


def tile_raster_images(X, img_shape, tile_shape, tile_spacing=(0, 0),
                       scale_rows_to_unit_interval=True,
                       output_pixel_vals=True):
  """
  Transform an array with one flattened image per row, into an array in
  which images are reshaped and layed out like tiles on a floor.

  This function is useful for visualizing datasets whose rows are images,
  and also columns of matrices for transforming those rows
  (such as the first layer of a neural net).

  :type X: a 2-D ndarray or a tuple of 4 channels, elements of which can
  be 2-D ndarrays or None;
  :param X: a 2-D array in which every row is a flattened image.

  :type img_shape: tuple; (height, width)
  :param img_shape: the original shape of each image

  :type tile_shape: tuple; (rows, cols)
  :param tile_shape: the number of images to tile (rows, cols)

  :param output_pixel_vals: if output should be pixel values (i.e. int8
  values) or floats

  :param scale_rows_to_unit_interval: if the values need to be scaled before
  being plotted to [0,1] or not


  :returns: array suitable for viewing as an image.
  (See:`PIL.Image.fromarray`.)
  :rtype: a 2-d array with same dtype as X.

  """

  assert len(img_shape) == 2
  assert len(tile_shape) == 2
  assert len(tile_spacing) == 2

  # The expression below can be re-written in a more C style as
  # follows :
  #
  # out_shape = [0,0]
  # out_shape[0] = (img_shape[0] + tile_spacing[0]) * tile_shape[0] -
  #                tile_spacing[0]
  # out_shape[1] = (img_shape[1] + tile_spacing[1]) * tile_shape[1] -
  #                tile_spacing[1]
  out_shape = [(ishp + tsp) * tshp - tsp for ishp, tshp, tsp
                      in zip(img_shape, tile_shape, tile_spacing)]

  if isinstance(X, tuple):
      assert len(X) == 4
      # Create an output numpy ndarray to store the image
      if output_pixel_vals:
          out_array = np.zeros((out_shape[0], out_shape[1], 4), dtype='uint8')
      else:
          out_array = np.zeros((out_shape[0], out_shape[1], 4), dtype=X.dtype)

      #colors default to 0, alpha defaults to 1 (opaque)
      if output_pixel_vals:
          channel_defaults = [0, 0, 0, 255]
      else:
          channel_defaults = [0., 0., 0., 1.]

      for i in xrange(4):
          if X[i] is None:
              # if channel is None, fill it with zeros of the correct
              # dtype
              out_array[:, :, i] = np.zeros(out_shape,
                      dtype='uint8' if output_pixel_vals else out_array.dtype
                      ) + channel_defaults[i]
          else:
              # use a recurrent call to compute the channel and store it
              # in the output
              out_array[:, :, i] = tile_raster_images(X[i], img_shape, tile_shape, tile_spacing, scale_rows_to_unit_interval, output_pixel_vals)
      return out_array

  else:
      # if we are dealing with only one channel
      H, W = img_shape
      Hs, Ws = tile_spacing

      # generate a matrix to store the output
      out_array = np.zeros(out_shape, dtype='uint8' if output_pixel_vals else X.dtype)


      for tile_row in xrange(tile_shape[0]):
          for tile_col in xrange(tile_shape[1]):
              if tile_row * tile_shape[1] + tile_col < X.shape[0]:
                  if scale_rows_to_unit_interval:
                      # if we should scale values to be between 0 and 1
                      # do this by calling the `scale_to_unit_interval`
                      # function
                      this_img = scale_to_unit_interval(X[tile_row * tile_shape[1] + tile_col].reshape(img_shape))
                  else:
                      this_img = X[tile_row * tile_shape[1] + tile_col].reshape(img_shape)
                  # add the slice to the corresponding position in the
                  # output array
                  out_array[
                      tile_row * (H+Hs): tile_row * (H + Hs) + H,
                      tile_col * (W+Ws): tile_col * (W + Ws) + W
                      ] \
                      = this_img * (255 if output_pixel_vals else 1)
      return out_array


class Tee(object):
    """
    Utility that duplicates stdout and stderr to a callable pipe,
    inspired by tee command.

    Sample usage:

    >>> pipe = RabbitPipe(conn, queue_name='logs', exchange_name='logs')
    >>> sys.stdout = Tee('stdout', pipe)
    >>> sys.stderr = Tee('stderr', pipe)
    """

    def __init__(self, stdname, *pipes):
        if stdname not in ('stdout', 'stderr'):
            raise Exception("`stdname` must be either 'stdout' or 'stderr'")

        for pipe in pipes:
            if not callable(pipe):
                raise Exception("`pipe` must be callable")
    
        self.pipes = pipes
        self.stdname = stdname
        self.stdoe = getattr(sys, self.stdname)

    def close(self):
        self.flush()
        setattr(sys, self.stdname, self.stdoe)

    def write(self, data):
        self.stdoe.write(data)
        for pipe in self.pipes:
            pipe(data)
 
    def flush(self) :
        self.stdoe.flush()
