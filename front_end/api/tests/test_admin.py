import random
import pytest
from job.models import PredictEnsemble, Predict

pytestmark = pytest.mark.django_db


@pytest.mark.xfail
def test_get_ensemble(client, user, trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    predict_ensemble = PredictEnsemble.objects.create(
        user=trained_mrnn_ensemble.user,
        input_data='1,2;3,4;\n5,6'
    )
    Predict.objects.create(iteration_id=lm1_iter, ensemble=predict_ensemble)
    Predict.objects.create(iteration_id=lm2_iter, ensemble=predict_ensemble)
    url = get_url('ensemble-detail', kwargs={"pk": ensemble.pk})
    response = client.get(url)
    assert response.status_code == 403
    url = get_url('ensemble-detail', kwargs={"pk": ensemble.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 404
    lm = ensemble.learn_models.all()[0]
    url = get_url('model-detail', kwargs={"pk": lm.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 404
    url = get_url('predict-detail', kwargs={"pk": predict_ensemble.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 404
    user.is_superuser = True
    user.save()
    url = get_url('ensemble-detail', kwargs={"pk": ensemble.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 200
    lm = ensemble.learn_models.all()[0]
    url = get_url('model-detail', kwargs={"pk": lm.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 200
    url = get_url('predict-detail', kwargs={"pk": predict_ensemble.pk},
                  params=[('key', user.apikey.key)])
    response = client.get(url)
    assert response.status_code == 200
