import numpy as np
import subprocess as sp
from PIL import Image
from math import ceil
from ..exception import DataFileError
from ..shared.fileutils import (open_file, open_bz, open_gz,
                                Archive, InvalidArchive)


class ProcessCall(object):
    def __init__(self, proc, *args):
        self.args = [str(a) for a in args]
        self.process = [proc] + self.args

    def call(self):
        proc = sp.Popen(self.process, stdout=sp.PIPE, stderr=sp.PIPE)
        content, errors = proc.communicate()
        return content, errors


def open_datafile(dataset, member=None):
    try:
        if dataset.endswith('gz'):
            for line in open_gz(dataset):
                yield line
        elif dataset.endswith('bz'):
            for line in open_bz(dataset):
                yield line
        elif dataset.endswith('zip'):
            archive = Archive(dataset)
            #TODO: remove it
            if member is None:
                member = archive.get_members()[0]
            for line in archive.open_member(member):
                yield line
        else:
            for line in open_file(dataset):
                yield line
    except (IndexError, InvalidArchive):
        raise DataFileError("Invalid ZIP file.")
    except Exception:
        raise DataFileError("Error while reading datafile.")


def shuffle(data, seed=777):
    rng = np.random.RandomState(seed)
    rng.shuffle(data)


def to_mrnn_shape(data):
    return data.transpose(1, 0, 2)


def to_normal_shape(data):
    return to_mrnn_shape(data)


def extend_with_nans(batches):
    T = batches[0].shape[0]
    shape = batches[0].shape
    for i in range(1, len(batches)):
        shape = (T - batches[i].shape[0], batches[i].shape[1], batches[i].shape[2])
        aa = np.tile(np.nan, shape)
        batches[i] = np.vstack((batches[i], aa))
    return np.hstack(batches)

def thumbnail_kludge(img, min_d):
    """Calculate the proper target aspect ratio to force img's *smaller*
    dimension to match min_d (rather than its larger dimension) and then
    pass to Image.thumbnail.

    The larger dimension has to "stick out past" min_d
    so that when the nd_array representation of the image is cropped in a
    later step, it results in a square of size (min_d, min_d), not a
    rectangle whose long side is min_d and whose short side is <min_d.

    Used for image dataset creation in ersatz/data/images.py
    """
    small_d, big_d = sorted(img.size)
    reverse = tuple([small_d,big_d]) != img.size
    big_d = int(ceil(float(big_d) / small_d * min_d))
    small_d = min_d #don't move this up, big_d has to calc first
    target = (big_d, small_d) if reverse else (small_d, big_d)
    img.thumbnail(target, Image.ANTIALIAS)
    # added ceil above in an effort to mitigate an issue: thumbnail
    # not returning exact target size (e.g. 160x119 instead of 160x120).
    # Haven't tested this solution heavily. See this gist for 
    # an alternate method: https://gist.github.com/olooney/1601455


def nd_centercrop(nd_arr, target_size): 
    """Crop the n-dimensional numpy array representation of a 2D image
    to a square of target_size by first calculating the appropriate
    offsets and then slicing the array.

    Used for image dataset creation in ersatz/data/images.py
    """
    size = np.array(nd_arr.shape[:2])
    offsets = (size-np.array(target_size))/2
    return nd_arr[offsets[0]:offsets[0]+target_size[0],
                  offsets[1]:offsets[1]+target_size[1]]
