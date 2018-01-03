import cPickle as pickle
import numpy as np
from .. import get_logger
from .csv import GeneralDataset
from .utils import shuffle
from ..shared.cifar import ConvImage
from ..shared.fileutils import Archive


log = get_logger('ersatz.data.images')
IMAGE_EXT = ('.jpeg', '.jpg', '.bmp', '.png')
OSX_DEBUG_FLAG = False


def get_data_size(archive, members):
    count = 0
    min_size = 128
    for m in members:
        im = ConvImage.from_archive(archive, m)
        try:
            min_size = min(min_size, min(im.size))
        except:
            log.error('Error while reading image size from archive')
            continue
        count += 1
    if min_size % 2: #fixes division rounding bug in ConvImage.to_square 
        min_size -= 1
    return count, min_size


class ImageDataset(GeneralDataset):
    def __init__(self, **kwargs):
        super(ImageDataset, self).__init__()
        self.source_data_type = "IMAGES"

    def _load_source(self, source_file, **kwargs):
        with Archive(source_file) as archive:
            if OSX_DEBUG_FLAG:
                import zipfile
                with zipfile.ZipFile(source_file) as zfile:
                    members = zfile.namelist()
            else:
                members = archive.get_members()
            members = [m for m in members if m.lower().endswith(IMAGE_EXT)]
            # Removes dotted and misc. forbidden files prior to processing.
            members = [m for m in members if archive.get_img_class(m)]
            shuffle(members)
            labels = set([archive.get_img_class(m) for m in members])
            try:
                labels.remove(None)
            except KeyError:
                pass
            self.labels = dict(zip(labels, range(len(labels))))
            mark = 0
            self.filenames = []
            samples, size = get_data_size(archive, members)
            data = np.empty((samples, size**2 * 3), dtype=np.uint8)
            output = np.empty((samples, ), dtype=np.uint8)
            for i, member in enumerate(members):
                img = ConvImage.from_archive(archive, member)
                try:
                    img.load()
                except:
                    continue
                try:
                    img.to_rgb(allow_grayscale=True)
                except ValueError:
                    continue
                try:
                    img.to_size(size)
                except ValueError:
                    continue
                data[mark] = img.to_array()
                output[mark] = self.labels[archive.get_img_class(member)]
                self.filenames.append(member.split('/')[-1])
                mark += 1
        data = data[0:mark, :]
        self.output = output[0:mark]
        return data

    def _load(self, dfile):
        super(ImageDataset, self)._load(dfile)
        self.labels = pickle.loads(dfile['data'].attrs['labels'])
        self.filenames = pickle.loads(dfile['data'].attrs['filenames'])

    def _dump(self, dfile):
        super(ImageDataset, self)._dump(dfile)
        dfile['data'].attrs['labels'] = pickle.dumps(self.labels, protocol=0)
        dfile['data'].attrs['filenames'] = pickle.dumps(self.filenames, protocol=0)

    def get_training_data(self):
        return self.data

    def get_predict_data(self):
        pass

    def _apply_filter(self, data, name, params):
        if name == 'split':
            data, self.output, self.filenames = filter_split(
                data, self.output, self.filenames,
                params['start'], params['end']
            )
        else:
            raise Exception('No such filter %s' % name)
        return data


def filter_split(data, output, filenames, start, end):
    start = int(round(data.shape[0] * (start / 100.0)))
    end = int(round(data.shape[0] * (end / 100.0)))
    data = data[start:end]
    output = output[start:end]
    filenames = filenames[start:end]
    return data, output, filenames


"""Dev Notes to Self:

The changes that are required to the ErsatzDataProvider that feeds into
cuda-convnet are subtle and are centered on *when* image to nd_array conversion
is performed. Right now that's right before training, but the new idea is to
convert everything to squared off nd_arrays at dm_worker parse time with all
user-specified filters applied. Additionally, in the course of this upfront
conversion, the images are cropped to squares with side length equal to the
lowest common dimension in the dataset.

These cropped nd_arrays are then stored to s3 in hdf5 format along with label
information. All the functionality I've described so far is encapsulated in the
ImageDataset class.

When the time comes for cuda-convnet to do its thing, it calls on the new
ErsatzDataProvider (EDP2) class to retrieve the dataset that it needs from s3.
EDP2 has to do three things:
    (1) spin up another provider object to help it, HDF5ImagesDataProvider.
        HIDP fetches the dataset from s3.
    (2) HIDP performs a final resize of the images to the size specified for
        training. IDS only scaled and cropped the images down to the minimum size
        necessary for them to be compatible with one another. IDS leaves them
        as big as possible so that the user has the widest latitude to train
        at different sizes. For example, IDS will have normalized everything to
        120x120; the user specifies image_size=32, so EDP2 has to do a final
        rescaling.
    (3) Segment the nd_array into batches (for efficient gpu processing) and
        yield those batches to the convnet trainer on demand.

So where are all these EDP2 responsibilities being handled currently?
    (1) Current EDP instantiates the helper object ArchivedImagesDataProvider
        which loads a raw image archive from s3, parses its labels, and converts
        to nd_arrays. [ersatz.data.cifar_provider]
    (2) [ersatz.shared.cifar]
    (3) [ersatz.shared.cifar]
"""
