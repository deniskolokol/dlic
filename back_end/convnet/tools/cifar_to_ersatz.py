import cPickle
import os
import numpy as np

DATA = 'cifar-10-py-colmajor'


with open(os.path.join(DATA, 'batches.meta'), 'rb') as f:
    meta_data = cPickle.load(f)

batch = {}
for i in range(1, 7):
    with open(os.path.join(DATA, 'data_batch_' + str(i)), 'rb') as f:
        data = cPickle.load(f)
    filenames = np.array(data['filenames']).reshape((10000,1))
    labels = np.array(data['labels'])
    for cls in range(10):
        class_index = (labels == cls).reshape((10000,))
        class_data = data['data'][:, class_index]
        class_labels = labels[class_index].reshape((-1, 1))
        class_filenames = filenames[class_index].reshape((-1, 1))
        if cls in batch:
            batch[cls]['data'] = np.hstack((batch[cls]['data'], class_data))
            batch[cls]['labels'] = np.vstack((batch[cls]['labels'], class_labels))
            batch[cls]['filenames'] = np.vstack((batch[cls]['filenames'], class_filenames))
        else:
            batch[cls] = {}
            batch[cls]['data'] = class_data
            batch[cls]['labels'] = class_labels
            batch[cls]['filenames'] = class_filenames

out = open('/tmp/test', 'wb')
cPickle.dump({'meta': meta_data, 'data': batch.values()}, out, 2)
out.close()
