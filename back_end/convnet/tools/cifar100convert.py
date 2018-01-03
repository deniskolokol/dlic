import cPickle
import os
import numpy as np

CIFAR_100_DIR = 'cifar-100-py'
CIFAR_20_DIR = 'cifar-20-py'


with open('meta' ,'rb') as f:
    meta_data = cPickle.load(f)
with open('test' ,'rb') as f:
    test_data = cPickle.load(f)
with open('train' ,'rb') as f:
    train_data = cPickle.load(f)
if not os.path.exists(CIFAR_20_DIR):
    os.mkdir(CIFAR_20_DIR)
if not os.path.exists(CIFAR_100_DIR):
    os.mkdir(CIFAR_100_DIR)

num_cases_per_batch = 10000
num_vis = 3072
train_data['data'] = train_data['data'].transpose()
test_data['data'] = test_data['data'].transpose()
data_mean = train_data['data'].mean(axis=1).reshape((num_vis,1)).astype('float32')


def create_meta(cdir, labels):
    new_meta = {'num_cases_per_batch': num_cases_per_batch,
                'num_vis': num_vis,
                'data_mean': data_mean,
                'label_names': labels}
    with open(os.path.join(cdir, 'batches.meta'), 'w') as f:
        cPickle.dump(new_meta, f, 2)

def create_test(cdir, labels):
    new_test = {'data': test_data['data'],
                'batch_label': test_data['batch_label'],
                'labels': labels,
                'filenames': test_data['filenames']}
    with open(os.path.join(cdir, 'data_batch_6'), 'w') as f:
        cPickle.dump(new_test, f, 2)

def create_train(cdir, labels):
    temp = []
    for i in range(5):
        new_train = {'data': train_data['data'][:, i * 10000:(i + 1) * 10000],
                    'batch_label': train_data['batch_label'],
                    'labels': labels[i * 10000:(i + 1) * 10000],
                    'filenames': train_data['filenames'][i * 10000:(i + 1) * 10000]}
        assert len(new_train['labels']) == 10000
        assert len(new_train['filenames']) == 10000
        with open(os.path.join(cdir, 'data_batch_' + str(i + 1)), 'w') as f:
            cPickle.dump(new_train, f, 2)
        temp.append(new_train['data'])
    temp = np.hstack(temp)
    assert temp.shape == (3072, 50000)
    assert (temp == train_data['data']).all()


create_meta(CIFAR_100_DIR, meta_data['fine_label_names'])
create_meta(CIFAR_20_DIR, meta_data['coarse_label_names'])
create_test(CIFAR_100_DIR, test_data['fine_labels'])
create_test(CIFAR_20_DIR, test_data['coarse_labels'])
create_train(CIFAR_100_DIR, train_data['fine_labels'])
create_train(CIFAR_20_DIR, train_data['coarse_labels'])
