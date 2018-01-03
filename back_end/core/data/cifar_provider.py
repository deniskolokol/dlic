import io
import traceback
from PIL import Image
import numpy as np
from ersatz import aws
from ersatz.shared.fileutils import Archive
from ersatz.shared.cifar import images_to_batch


class ArchivedImagesDataProvider(object):

    IMAGE_EXT = ('.jpeg', '.jpg', '.bmp', '.png')

    def __init__(self, key, img_size=32, shuffle=True):
        self.key = key
        self.img_size = img_size
        f = aws.S3Key(self.key).get()
        self.archive = Archive(f)
        self.labels = {}

        members = self.archive.get_members()
        for member in members:
            if member.lower().endswith(self.IMAGE_EXT):
                klass = self.archive.get_img_class(member)
                self.labels.setdefault(klass, []).append(member)
        self.label_list = sorted(self.labels.iterkeys())

    def get_class_sizes(self):
        return [len(self.labels[l]) for l in self.label_list]

    def get_class_labels(self):
        return self.label_list

    def get_num_classes(self):
        return len(self.labels)

    def get_meta(self):
        self.metabatch = {
            'data_mean': np.zeros((self.img_size * self.img_size, 1)),
            'num_vis': self.img_size * self.img_size,
            'label_names': self.label_list
        }
        return self.metabatch

    def get_class_chunk(self, class_number, slice_):
        label = self.label_list[class_number]
        img_files = self.labels[label][slice_]
        cnt = len(img_files)

        def iter_images():
            inmemory_fp = io.BytesIO()
            for fn in img_files:

                inmemory_fp.seek(0)
                fp = self.archive.open_raw_member(fn)
                inmemory_fp.write(fp.read())
                inmemory_fp.truncate()
                inmemory_fp.seek(0)
                try:
                    im = Image.open(inmemory_fp)
                except:
                    print 'Cant open image {0} in archive {1}'.format(fn, self.key)
                    traceback.print_exc()
                    print 'Continue...'
                    continue
                yield im

        chunk = images_to_batch(iter_images(), count=cnt, size=self.img_size)
        chunk = chunk.transpose()
        labels = np.array([class_number] * cnt).reshape((cnt, 1))
        return {'data': chunk, 'labels': labels}
