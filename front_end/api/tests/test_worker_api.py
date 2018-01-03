import json
import pytest
from django.core.urlresolvers import reverse
from django.conf import settings
from rest_framework import status
from job.models import LearnModel


pytestmark = pytest.mark.django_db


def test_model_to_train(ensemble_all_types, client):
    learn_model = LearnModel.objects.get(model_name='MLP_MAXOUT_CONV')
    ens = learn_model.ensemble
    ens.queue_key = 'asd'
    ens.save()
    data = {
        'model': learn_model.id,
        'state': 'TRAIN',
        'worker_key': settings.WORKER_KEY,
        'queue_key': ens.queue_key,
        'model_params': {
            "maxnum_iter": 100,
            "percent_batches_per_iter": 100,
            "save_freq": 25,
            "batch_size": 128,
            "learning_rate": {
                "init": 0.1,
                "constant": True
            },
            "momentum": {
                "init": 0.1,
                "constant": True
            },
            "layers": [
                {
                    "max_kernel_norm": 0.9,
                    "num_pieces": 2,
                    "pool_stride": 2,
                    "pad": 0,
                    "num_units": 48,
                    "layer_name": "h0",
                    "type": "maxout_convolution",
                    "pool_shape": 4,
                    "kernel_shape": 8,
                    "irange": 0.0005
                },
            ]
        },
    }
    response = client.post(reverse('api_train_status'),
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    model_params = LearnModel.objects.get(pk=learn_model.pk).model_params
    assert model_params == data['model_params']
