import zipfile
import tarfile
import tempfile
import cPickle
import unipath
import numpy as np
import shutil
from PIL import Image
from io import BytesIO
from unipath import Path

VALID_EXT = ('.jpg', '.jpeg', '.png', '.bmp')


class BatchWriter(object):
    def __init__(self, data_path, img_size=32,
                 channels=3, max_batch_size=10000):
        self.data_path = Path(data_path).child('batches')
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True)
        self.img_size = img_size
        self.channels = channels
        self.max_batch_size = max_batch_size
        self.datasets = {}
        self.next_batch = 1
        self.train_range = None
        self.test_range = None

    def prepare_training(self, train_dset, test_dset):
        if train_dset is not None:
            train_data = self.preprocess_data(train_dset.data)
            train_batch_size = self.calculate_batch_size(train_data.shape[0])
            self.train_range = self.dump_batches(train_data,
                                                 train_dset.output,
                                                 train_dset.filenames,
                                                 train_batch_size)
        test_data = self.preprocess_data(test_dset.data)
        test_batch_size = self.calculate_batch_size(test_data.shape[0])
        self.test_range = self.dump_batches(test_data,
                                            test_dset.output,
                                            test_dset.filenames,
                                            test_batch_size)
        if train_dset is None:
            label_names = test_dset.labels.copy()
            data = test_data
            batch_size = test_batch_size
        else:
            label_names = train_dset.labels.copy()
            label_names.update(test_dset.labels)
            data = np.vstack((train_data, test_data))
            batch_size = train_batch_size
        self.dump_meta_batch(data, label_names, batch_size)

    def dump_meta_batch(self, data, label_names, batch_size):
        mean = data.transpose().mean(axis=1).reshape((-1, 1))
        data_path = self.data_path.child('batches.meta')
        self.write_cifar_meta_batch(data_path, mean, label_names, batch_size)

    def dump_batches(self, data, output, filenames, batch_size):
        start_batch = self.next_batch
        for i, mark in enumerate(range(0, data.shape[0], batch_size)):
            slice_ = slice(mark, mark + batch_size)
            self.write_cifar_batch(
                self.data_path.child('data_batch_' + str(self.next_batch)),
                data[slice_].transpose(),
                output[slice_],
                filenames[slice_]
            )
            self.next_batch += 1
        return start_batch, self.next_batch - 1

    def write_cifar_batch(self, data_path, data, labels, filenames):
        data = {
            'batch_label': '',
            'labels': labels,
            'data': data,
            'filenames': filenames,
        }
        with open(data_path, 'wb') as f:
            cPickle.dump(data, f)

    def write_cifar_meta_batch(self, data_path, mean, label_names, batch_size):
        data = {
            'data_mean': mean,
            'label_names': label_names,
            'num_cases_per_batch': batch_size,
            'num_vis': mean.shape[0]
        }
        with open(data_path, 'wb') as f:
            cPickle.dump(data, f)

    def preprocess_data(self, dset_data):
        dset_size = int(np.sqrt(dset_data.shape[1] / self.channels))
        data = np.empty((dset_data.shape[0], self.img_size**2 * self.channels),
                        dtype=np.uint8)
        if self.img_size != dset_size:
            for i in range(data.shape[0]):
                image = ConvImage.from_array(dset_data[i],
                                             self.channels,
                                             dset_size)
                image.to_size(self.img_size)
                data[i] = image.to_array()
            return data
        return dset_data

    def get_data_options(self):
        return ['--data-path=%s' % self.data_path,
                '--train-range=%s-%s' % self.train_range,
                '--test-range=%s-%s' % self.test_range,
                '--img-size=%s' % self.img_size,
                '--data-provider=cifar']

    def get_data_options_test(self):
        return ['--data-dir=%s' % self.data_path,
                '--test-range=%s-%s' % self.test_range,
                '--is-dataset=1']

    def calculate_batch_size(self, data_size):
        if data_size % self.max_batch_size == 0:
            return self.max_batch_size
        c = data_size / self.max_batch_size + 1
        return data_size / c


class ConvImage(object):
    def __init__(self, image):
        self.image = image

    @classmethod
    def from_archive(cls, archive, member):
        fp = BytesIO(archive.open_raw_member(member).read())
        return cls(Image.open(fp))

    @classmethod
    def from_array(cls, data, channels, size):
        rval = data.reshape((channels, size, size)).transpose([1, 2, 0])
        return cls(Image.fromarray(rval))

    def load(self):
        self.image.load()

    @property
    def size(self):
        return self.image.size

    def to_size(self, size):
        size_tuple = (size, size)
        if self.image.size != size_tuple:
            self.to_square()
            self.image.thumbnail(size_tuple, Image.ANTIALIAS)

    def to_square(self):
        w, h = self.image.size
        if w != h:
            min_dim = int(min(w, h))
            self.image = self.image.crop((w / 2 - min_dim / 2,
                                          h / 2 - min_dim / 2,
                                          w / 2 + min_dim / 2,
                                          h / 2 + min_dim / 2))

    def to_rgb(self, allow_grayscale=True):
        if self.image.mode == 'RGBA':
             self.image = rgba_to_rgb(self.image)
        elif self.image.mode == 'CMYK':
            self.image = self.image.convert('RGB')
        elif self.image.mode in ('L', 'P'):
            if allow_grayscale:
                self.image = grayscale_to_rgb(self.image)
        if self.image.mode != 'RGB':
            raise ValueError('Unknown image format')
        return self.image

    def to_array(self):
        return np.array(self.image, order='C')\
            .transpose([2, 0, 1]).flatten('C')


class tempdir(object):
    def __enter__(self):
        self.tempdir = unipath.Path(tempfile.mkdtemp())
        return self.tempdir

    def __exit__(self, type_, value, traceback):
        shutil.rmtree(self.tempdir)


class cwd(object):
    def __init__(self, cwd):
        self.prev_cwd = unipath.FSPath.cwd()
        self.cwd = unipath.Path(cwd)
        if not self.cwd.exists():
            self.cwd.mkdir(parents=True)

    def __enter__(self):
        self.cwd.chdir()
        return self.cwd

    def __exit__(self, type_, value, traceback):
        self.prev_cwd.chdir()


def image_as_rgb(image, skip_grayscale=True, skip_unknown=True):
    if image.mode == 'RGBA':
        image = rgba_to_rgb(image)
    elif image.mode == 'CMYK':
        image = image.convert('RGB')
    elif image.mode in ('L', 'P'):
        if skip_grayscale:
            return None
        image = grayscale_to_rgb(image)
    elif image.mode != 'RGB':
        if skip_unknown:
            return None
        raise ValueError('Unknown image format')
    return image


def image_to_cifar(image, size=32):
    """
    Convert PIL image to cifar image format

    Parameters
    ----------
    image: PIL.Image (loaded)
        image in a PIL format
    size: int, optional
        size of the image; default: 32
        original cifar images has size 32 (32x32 pixels)

    Returns
    -------
    rval: ndarray
        image in cifar format
    """

    image = image_as_rgb(image, skip_grayscale=False, skip_unknown=False)
    image = resize_image(image, size)
    rval = np.array(image, order='C')
    rval = rval.transpose([2, 0, 1]).flatten('C')
    return rval


def crop_to_square(image):
    w, h = image.size
    if w != h:
        min_dim = int(min(w, h))
        image = image.crop((w / 2 - min_dim / 2, h / 2 - min_dim / 2,
                            w / 2 + min_dim / 2, h / 2 + min_dim / 2))
    return image


def resize_image(image, size):
    size_tuple = (size, size)
    if image.size != size_tuple:
        image = crop_to_square(image)
        image.thumbnail(size_tuple, Image.ANTIALIAS)
    return image


def rgba_to_rgb(image, color=(255, 255, 255)):
    """
    Alpha composite an RGBA Image with a specified color.

    Parameters
    ----------
    image: PIL.Image (loaded)
        RGBA image in PIL format
    color: tuple, optional
        tuple of 3 int, describes background of rgb image

    Returns
    -------
    rval: PIL.Image
        RGB image in PIL format

    Notes
    -----
    http://stackoverflow.com/questions/9166400/convert-rgba-png-to-rgb-with-pil
    """

    rval = Image.new('RGB', image.size, color)
    rval.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return rval


def grayscale_to_rgb(image):
    """
    Convert grayscale image to rgb

    Parameters
    ----------
    image: PIL.Image (loaded)
        grayscale image in PIL format

    Returns
    -------
    rval: PIL.Image
        rgb image in PIL format
    """

    rval = Image.new('RGB', image.size)
    rval.paste(image)
    return rval


def cifar_image_to_pil(image, size=32, channels=3):
    """
    Convert from cifar image format to PIL image

    Parameters
    ----------
    image: ndarray
        image in cifar format
    size: int, optional
        size of the image; default: 32
        original cifar images has size 32 (32x32 pixels)
    channels: int, optional
        channels in image; default: 3
        original cifar images has 3 channels

    Returns
    -------
    rval: PIL.Image
        image in a PIL format
    """

    rval = image.reshape((channels, size, size)).transpose([1, 2, 0])
    return Image.fromarray(rval)


def images_to_batch(images, count, size=32, channels=3):
    """
    Convert iterable of images to cifar batch

    Parameters
    ----------
    images: sequence
        sequence of images in PIL.Image format
    count: int
        number of images to process
    size: int, optional
        size of the image; default: 32
    channels: int, optional
        channels in image; default: 3

    Returns
    -------
    batch_data: ndarray
       ndarray of all images
    """

    bytes = size * size * channels
    batch_data = np.empty((count, bytes), dtype=np.uint8)
    for i, image in enumerate(images):
        try:
            image.load()
        except IOError:
            # corrupted images
            pass
        batch_data[i, :] = image_to_cifar(image, size)
    return batch_data


def files_to_batch(files):
    images = (Image.open(fp) for fp in files)
    count = len(files)
    return images_to_batch(images, count)


def dir_to_cifar(source):
    labels = []
    files = []
    label_encoder = {}
    label_code = 0
    with cwd(source) as source:
        for class_path in source.listdir():
            fs = unipath.Path(class_path).walk(
                filter=lambda x: x.isfile() and x.lower().endswith(VALID_EXT)
            )
            fs = [x.lstrip('./') for x in fs]
            files.extend(fs)
            labels.extend([label_code] * len(fs))
            label_encoder[class_path.name] = label_code
            label_code += 1
        batch = files_to_batch(files)
    return batch, labels, [str(x) for x in files], label_encoder


def zip_to_cifar(zip_file):
    if not zipfile.is_zipfile(zip_file):
        raise ValueError('Not a zip file')
    z = zipfile.ZipFile(zip_file, mode='r')
    with tempdir() as d:
        with cwd(d):
            for member in z.namelist():
                z.extract(member)
            rval = dir_to_cifar('.')
    return rval


#TODO: DANGEROUS do not use it on user's files, extractall not safe, read docs
def tar_to_cifar(tar_file):
    tar = tarfile.open(tar_file, 'r:gz')
    with tempdir() as d:
        with cwd(d):
            tar.extractall()
            rval = dir_to_cifar('.')
    return rval


def save_cifar_batch(fp, batch, labels, files, transpose=False):
    rng = np.random.RandomState(777)
    rng.shuffle(batch)
    rng.seed(777)
    rng.shuffle(labels)
    rng.seed(777)
    rng.shuffle(files)
    size = batch.shape[0] / 6
    for i in range(6):
        start = size*i
        stop = start + size
        minibatch = batch[start:stop, :]
        if transpose:
            minibatch = minibatch.transpose()
        data = {
            'batch_label': '',
            'labels': labels[start:stop],
            'data': minibatch,
            'filenames': files[start:stop],
        }
        with open(fp + '_' + str(i+1), 'wb') as f:
            cPickle.dump(data, f)


def save_batches_meta(fp, batch, encoder, num_cases_per_batch,
                      num_vis=32 * 32 * 3, transpose=False):
    if transpose:
        mean = batch.transpose().mean(axis=1).reshape((-1, 1))
    else:
        mean = batch.mean(axis=0).reshape((1, -1))
    data = {
        'data_mean': mean,
        'label_names': encoder.keys(),
        'num_cases_per_batch': num_cases_per_batch,
        'num_vis': num_vis
    }
    with open(fp, 'wb') as f:
        cPickle.dump(data, f)


def unpack_cifar_batch(data, dest):
    """
    Unpacking cifar file format to directory

    Parameters
    ----------
    data: dict
        cifar batch file
    dest: str
        path where store resulting data
    """

    batch = data['data']
    with cwd(dest):
        for l in set(data['labels']):
            unipath.Path(l).mkdir()
        for i, (f, label) in enumerate(zip(data['filenames'], data['labels'])):
            image = cifar_image_to_pil(batch[i])
            image.save(unipath.Path(label).child(unipath.Path(f).name))


def load_cifar_batch(fp, transpose=False):
    with open(fp) as f:
        data = cPickle.load(f)
    if transpose:
        data['data'] = data['data'].transpose()
    return data


def unpack_cifar10():
    files = []
    dest = '/tmp/result'
    shutil.rmtree(dest)
    for i in range(1, 6):
        files.append('./cifar-10-batches-py/data_batch_' + str(i))
    files.append('./cifar-10-batches-py/test_batch')
    for fn in files:
        data = load_cifar_batch(fn)
        unpack_cifar_batch(data, dest)


def construct_predict_batch(images):
    labels = [0] * len(images)
    data = images_to_batch((Image.open(i) for i in images), len(images)).transpose()
    mean = data.mean(axis=0)
    batch = {
        'batch_label': '',
        'labels': labels,
        'data': data,
        'filenames': [image.name for image in images]
    }
    return cPickle.dumps(batch), mean


def test_cifar10_convert():
    with tempdir() as td:
        data = load_cifar_batch('./cifar-10-batches-py/data_batch_1')
        unpack_cifar_batch(data, td)
        batch, labels, files, encoder = dir_to_cifar(td)
    batch = sorted(zip(batch, files), key=lambda x: data['filenames'].index(unipath.Path(x[1]).name))
    batch = zip(*batch)[0]
    assert (batch == data['data']).all()
    labels = sorted(zip(labels, files), key=lambda x: data['filenames'].index(unipath.Path(x[1]).name))
    labels = zip(*labels)[0]
    assert all(x == y for x, y in zip(labels, data['labels']))
