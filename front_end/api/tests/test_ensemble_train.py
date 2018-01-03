import random
import pytest
from django.core.urlresolvers import reverse
from job.models import TrainEnsemble, LearnModel, DeepNetModel

pytestmark = pytest.mark.django_db(transaction=True)


def test_new_ensemble_start(ensemble, patch_queue):
    lm1 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    lm2 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    ensemble.resume()
    queue = patch_queue['queue']
    ensemble = TrainEnsemble.objects.get(pk=ensemble.pk)
    data = {
        "config": None,
        "data_type": "TIMESERIES",
        "ensemble": ensemble.id,
        "models": [
            {
                "id": lm1.id,
                "model_params": {
                    "maxnum_iter": 20
                },
                "name": "MRNN",
                "out_nonlin": "SOFTMAX"
            },
            {
                "id": lm2.id,
                "model_params": {
                    "maxnum_iter": 20
                },
                "name": "MRNN",
                "out_nonlin": "SOFTMAX"
            }
        ],
        "options": {
            "max_timesteps": 97
        },
        "quantiles": None,
        "queue_key": ensemble.queue_key,
        "sp_results": "",
        "test_dataset": {
            "data": {
                "data_type": "TIMESERIES",
                "id": 2,
                "key": ensemble.test_dataset.data.key,
                "classes": {
                    "1": 121,
                    "0": 2951
                },
            u'num_columns': 0,
            u'with_header': False,
            'delimiter': '\s+',
            'dtypes': [],
            },

            "filters": [],
            "id": 2,
            "iscreated": False,
            "key": ensemble.test_dataset.key,
            "last_column_is_output": None,
            "norm_min_max": None,
            "quantiles": None,
            "version": 2,

        },
        "train_dataset": {
            "data": {
                "data_type": "TIMESERIES",
                "id": 1,
                "key": ensemble.train_dataset.data.key,
                "classes": {
                    "1": 121,
                    "0": 2951
                },
                u'num_columns': 0,
                u'with_header': False,
                'delimiter': "\s+",
                'dtypes': [],
            },
            "filters": [
                {
                    "name": "shuffle"
                }
            ],
            "id": 1,
            "iscreated": False,
            "key": ensemble.train_dataset.key,
            "last_column_is_output": None,
            "norm_min_max": None,
            "quantiles": None,
            "version": 2
        },
        "valid_dataset": None
    }
    assert len(queue) == 1
    assert queue[0] == data


def test_new_ensemble_start_no_auto_next(ensemble, patch_queue):
    LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    lm2 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    lm2.restart()
    queue = patch_queue['queue']
    assert len(queue) == 1
    msg = queue[0]
    data = [
        {
            "id": lm2.id,
            "model_params": {
                "maxnum_iter": 20
            },
            "name": "MRNN",
            "out_nonlin": "SOFTMAX"
        },
    ]
    assert msg['models'] == data


def test_model_restart_while_training(ensemble, client):
    lm1 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    lm2 = LearnModel.objects.create(
        ensemble=ensemble,
        model_name='MRNN'
    )
    data = {
        'iteration': 1,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    ensemble.resume()
    ensemble = TrainEnsemble.objects.get(pk=ensemble.pk)
    ensemble.state = ensemble.ST_TRAIN
    ensemble.save()
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    lm1.state = 'TRAIN'
    lm1.save()
    lm1.add_stat(data, '/s3.keya213')
    data.update({'iteration': 2, 'train_accuracy': 0.91})
    lm1.add_stat(data, '/s3.keyasdfadsf')
    data.update({'iteration': 3, 'train_accuracy': 0.95})
    lm1.add_stat(data, '/s3.keyasdfadsfsd')
    lm1.to_finish_state('1 2 3 4', '')
    lm2 = LearnModel.objects.get(pk=lm2.pk)
    lm2.state = 'TRAIN'
    lm2.save()
    data = {
        'iteration': 1,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    lm2.add_stat(data, '/s3.keya213')
    data.update({'iteration': 2, 'train_accuracy': 0.91})
    key = ensemble.user.apikey.key
    response = client.post(reverse('model-restart', kwargs={'pk': lm1.pk})
                           + '?key=' + key)
    assert response.status_code == 400
    lm1 = LearnModel.objects.get(pk=lm1.pk)
    assert lm1.state == 'FINISHED'
    assert lm1.stats.count() == 3


def test_sp(trained_mlp_ensemble, patch_queue, client):
    ensemble = trained_mlp_ensemble
    key = ensemble.user.apikey.key
    lm3 = DeepNetModel.objects.create(
        ensemble=ensemble,
        model_name='MLP_MAXOUT_CONV'
    )
    data = {
        'iteration': 10,
        'train_accuracy': 0.9,
        'test_accuracy': 0.8,
        'time': 60,
    }
    lm3.add_stat(data, '/s3.key')
    lm3.to_finish_state('31 32 33 34')
    lm = random.choice(
        ensemble.learn_models.all()
    )
    response = client.post(reverse('model-resume', kwargs={'pk': lm.pk})
                           + '?key=' + key)
    assert response.status_code == 200
    sp_results = ensemble.learn_models.exclude(pk=lm.pk) \
        .values_list('sp_results', flat=True)
    sp_results = '\n'.join(sp_results) + '\n'
    queue = patch_queue['queue']
    assert len(queue) == 1
    assert queue[0]['sp_results'] == sp_results
