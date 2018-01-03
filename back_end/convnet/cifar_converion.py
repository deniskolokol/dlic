#coding=utf-8
import cPickle
from PIL import Image
import os
import numpy as np


def image_to_cifar_array(pil_image, img_size=32):
    im = pil_image
    img_size_tuple = (img_size, img_size)

    if im.size != img_size_tuple:
        w, h = im.size
        if w != h:
            min_dim = min(w, h)
            im = im.crop((w / 2 - min_dim / 2, h / 2 - min_dim / 2, w / 2 + min_dim / 2, h / 2 + min_dim / 2))
            im = im.resize(img_size_tuple, Image.ANTIALIAS)
        else:
            im.thumbnail(img_size_tuple, Image.ANTIALIAS)

    arr = np.array(im, order='C')
    arr = arr.transpose([2, 0, 1]).flatten('C')
    return arr


def cifar_array_to_image(image_arr, img_size=32, channels=3):
    img_arr = image_arr.reshape((channels, img_size, img_size)).transpose([1, 2, 0])
    return Image.fromarray(img_arr)


def build_cifar_batch(image_file_list, labels, img_size=32, channels=3, batch_label=''):
    img_bytes = img_size * img_size * channels
    batch_data = np.zeros((img_bytes, len(image_file_list)), dtype=np.float32)
    for i, img_file in enumerate(image_file_list):
        im = Image.open(img_file)  # Image.fromstring(...)
        batch_data[:, i] = image_to_cifar_array(im, img_size)

    batch = {
        'batch_label': batch_label,
        'labels': labels,
        'data': batch_data,
        #'filenames': image_file_list, # uncomment if applicable
    }
    return cPickle.dumps(batch)

if __name__ == '__main__':
    print build_cifar_batch(['d:/Images2.jpg'], [0])

