from . import timeseries
from . import csv
from . import images
from .. import api
from ..aws import S3Key, save_to_s3
from ..conf import settings
from ..exception import ApiParamsError, AWSError
from .. import get_logger


log = get_logger('ersatz.api')


DATASETS_TYPES = {
    'GENERAL': csv.GeneralDataset,
    'TIMESERIES': timeseries.Timeseries,
    'IMAGES': images.ImageDataset
}


def load(train_dataset, test_dataset, valid_dataset):
    """
    Returns train, test and valid data with
    additional metadata if required by format.
    """
    train_data = get_dataset(train_dataset)
    test_data = get_dataset(test_dataset)
    valid_data = get_dataset(valid_dataset)
    train_data = None if train_data is None else train_data.get_training_data()
    test_data = None if test_data is None else test_data.get_training_data()
    valid_data = None if valid_data is None else valid_data.get_training_data()
    return train_data, test_data, valid_data


def load_dataset(dataset, key):
    dataset_file = S3Key(key).get()
    dataset.load(dataset_file=dataset_file)
    return dataset


def get_dataset(dataset_params):
    """
    Loads dataset from s3 if 'iscreated',
    otherwise loads from source and saves hdf5 file to s3.
    
    Warning!
    Because of the use if csvstat (see DM_Worker) for fast data load for
    'GENERAL' sources load_from_source doesn't actually fills dataset.data
    and dataset.output, but only creates hdf5.

    For the rest of files (images, timeseries) load_from_source fills
    dataset.data and dataset.output instantly.
    """
    if dataset_params is None:
        return None
    try:
        Dataset = DATASETS_TYPES[dataset_params['data']['data_type']]
        dataset_key = dataset_params['key']
        source_key = dataset_params['data']['key']
    except (KeyError, TypeError):
        log.critical('Invalid api message for dataset, stop processing.')
        raise ApiParamsError('Invalid format of datasets parameters',
                             show_to_user=False)
    dataset = Dataset()
    if (dataset_params['iscreated'] and
        dataset_params['version'] == settings.DATASET_VERSION):
        log.info('Dataset %s is already created, loading '
                  'without processing.' % dataset_key)
        load_dataset(dataset, dataset_key)
    else:
        log.info('Dataset %s was not created yet' % dataset_key)
        source_file = S3Key(source_key).get()

        log.info('Loading dataset from source file, applying filters...')
        dataset_file = prepare_dataset_file_dir(dataset_key)
        kwargs = prepare_dataset_params(dataset_params, dataset_file)
        dataset.load_from_source(source_file, **kwargs)
        if dataset_params['data']['data_type'] != 'GENERAL':
            dataset.save(dataset_file)

        log.info('Dataset %s created, saving to s3' % dataset_key)
        try:
            save_to_s3(dataset_file, dataset_key,
                       rewrite=dataset_params['iscreated'], interactive=True)
        except AWSError:
            log.warn('Dataset %s already exists on s3, but iscreated=False, '
                     'continue without saving' % dataset_key)
        else:
            params = {'id': dataset_params['id'],
                      'iscreated': True,
                      'version': settings.DATASET_VERSION}
            params.update(dataset.extra_params)
            api.post('/api/dataset/update/', params)

        if dataset_params['data']['data_type'] == 'GENERAL':
            log.info('Loading dataset %s for training' % dataset_key)
            load_dataset(dataset, dataset_key)
    log.info('Dataset %s ready for training' % dataset_key)
    return dataset


def prepare_dataset_file_dir(key):
    dataset_file = key.strip('/').split('/')
    dataset_file = settings.S3_CACHEDIR.child(*dataset_file)
    if not dataset_file.parent.exists():
        dataset_file.parent.mkdir(parents=True)
    return dataset_file


def prepare_dataset_params(parm, dsfile):
    _out = lambda parm, keys: dict((k, v) for k, v in parm.iteritems()
                                   if k in keys)
    out = {'version': settings.DATASET_VERSION, 'target': dsfile,
           'source_data_type': parm['data']['data_type']}
    out.update(_out(parm, ('filters',)))
    out.update(_out(parm['data'],
                    ('dtypes', 'classes', 'with_header', 'num_columns',
                     'min', 'max', 'mean', 'stdev')
                    )
              )
    return out
