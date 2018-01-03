import Image
import json
import pytest
import random
from job.models import PredictEnsemble, Predict
from rest_framework import status


pytestmark = pytest.mark.django_db


@pytest.fixture
def mrnn_predict(trained_mrnn_ensemble):
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
    return predict_ensemble


def test_list_predict(client, mrnn_predict, get_url):
    predict_ensemble = mrnn_predict
    user = predict_ensemble.user
    iterations = predict_ensemble.iterations.values_list('pk', flat=True)
    response = client.get(get_url('predict-detail',
                                  kwargs={'pk': predict_ensemble.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK
    rdata = json.loads(response.content)
    assert rdata == {
        'id': 1,
        'state': 'NEW',
        'error': None,
        'results': None,
        'dataset': None,
        'iterations': list(iterations),
        'predicting_time': 0.0,
        'input_data': '1,2;3,4;\n5,6',
    }


def test_create_mrnn_predict_input(client, trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = {
        'id': 1,
        'state': 'QUEUE',
        'error': None,
        'results': None,
        'dataset': None,
        'iterations': [lm1_iter, lm2_iter],
        'predicting_time': 0.0,
        'input_data': '1,2;3,4;\n4,5',
    }
    rdata = json.loads(response.content)
    assert rdata == data


def test_create_mrnn_predict_no_data(client, trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': ['Provide input_data or dataset field.']
    }


def test_create_mrnn_predict_both_data(client, trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
        'dataset': trained_mrnn_ensemble.test_dataset.pk,
        'input_data': '1,2;3,4\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'non_field_errors': [
            "input_data and dataset field mustn't be used together."
        ]
    }


def test_create_predict_on_shared(client, user,
                                  trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    assert ensemble.share()
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = {
        'id': 1,
        'state': 'QUEUE',
        'error': None,
        'results': None,
        'dataset': None,
        'iterations': [lm1_iter, lm2_iter],
        'predicting_time': 0.0,
        'input_data': '1,2;3,4;\n4,5',
    }
    rdata = json.loads(response.content)
    assert rdata == data


def test_create_predict_different_ensembles(client, get_url,
                                            get_trained_mrnn_ensemble):
    ensemble = get_trained_mrnn_ensemble()
    assert ensemble.share()
    ensemble2 = get_trained_mrnn_ensemble()
    user = ensemble2.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    lm3_iter = random.choice(
        ensemble2.learn_models.all()[1].stats.all().values_list('id',
                                                                flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter, lm3_iter],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {
            'iterations': 'Iterations must be from same train ensemble.'
        }
    }


def test_create_predict_miss_iterations(client,
                                        trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    data = {
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'iterations': 'This field is required.'}
    }


def test_create_predict_empty_iterations(client,
                                         trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    data = {
        'iterations': [],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'iterations': 'This field is required.'}
    }


def test_create_predict_extra_iterations(client,
                                         trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [1000000, lm1_iter, lm2_iter],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'iterations':
                   "Iterations with this ids don't exists: [1000000]"}
    }


def test_create_predict_invalid_iteration(client,
                                          trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    data = {
        'iterations': [10000],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'iterations':
                   "Iterations with this ids don't exists: [10000]"}
    }


def test_create_predict_invalid_iteration2(client,
                                           trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    data = {
        'iterations': ['z'],
        'input_data': '1,2;3,4;\n4,5\n\n',
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'iterations':
                   "This field must be a list of integers."}
    }


def test_delete_predict(client, mrnn_predict, get_url):
    user = mrnn_predict.user
    response = client.delete(get_url('predict-detail',
                                     kwargs={'pk': mrnn_predict.pk},
                                     params=[('key', user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_get_predict(client, mrnn_predict, get_url):
    user = mrnn_predict.user
    response = client.get(get_url('predict-detail',
                                  kwargs={'pk': mrnn_predict.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_200_OK


def test_predict_permission(client, mrnn_predict, user, get_url):
    response = client.get(get_url('predict-detail',
                                  kwargs={'pk': mrnn_predict.pk},
                                  params=[('key', user.apikey.key)]),
                          format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = client.delete(get_url('predict-detail',
                                     kwargs={'pk': mrnn_predict.pk},
                                     params=[('key', user.apikey.key)]),
                             format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_mrnn_predict_dataset(client, trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
        'dataset': trained_mrnn_ensemble.test_dataset.pk,
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = {
        'id': 1,
        'state': 'QUEUE',
        'error': None,
        'results': None,
        'dataset': ensemble.test_dataset.pk,
        'iterations': [lm1_iter, lm2_iter],
        'predicting_time': 0.0,
        'input_data': None,
    }
    rdata = json.loads(response.content)
    assert rdata == data


def test_update_predict(client, mrnn_predict, get_url):
    predict_ensemble = mrnn_predict
    user = predict_ensemble.user
    data = {'input_data': '1,2;'}
    response = client.put(get_url('predict-detail',
                                  kwargs={'pk': predict_ensemble.pk},
                                  params=[('key', user.apikey.key)]),
                          data=data,
                          format='json')
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_create_mrnn_predict_not_owned_dataset(client, data_set_ts,
                                               trained_mrnn_ensemble, get_url):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': [lm1_iter, lm2_iter],
        'dataset': data_set_ts.pk,
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_predict_images(client, trained_images_ensemble,
                               tmpdir, get_url, patch_upload_data_to_s3):
    ensemble = trained_images_ensemble
    user = ensemble.user
    ufile = tmpdir.join('image.jpg')
    im = Image.new('RGB', (50, 50))
    im.save(str(ufile))
    ufile.name = 'image.jpg'
    ufile2 = tmpdir.join('image2.jpg')
    im = Image.new('RGB', (50, 50))
    im.save(str(ufile2))
    ufile2.name = 'image2.jpg'
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': json.dumps([lm1_iter]),
        'file-0': ufile,
        'file-1': ufile2,
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='multipart')
    assert response.status_code == status.HTTP_201_CREATED
    data = {
        'id': 1,
        'state': 'QUEUE',
        'error': None,
        'results': None,
        'dataset': None,
        'iterations': [lm1_iter],
        'predicting_time': 0.0,
        'input_data': None,
    }
    rdata = json.loads(response.content)
    assert rdata == data


def test_create_predict_bad_images(client, trained_images_ensemble,
                                   tmpdir, get_url):
    ensemble = trained_images_ensemble
    user = ensemble.user
    ufile = tmpdir.join('image.jpg')
    ufile.write('asdasd')
    ufile.name = 'image.jpg'
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': json.dumps([lm1_iter]),
        'file-0': ufile
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='multipart')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': {'file-0': 'Bad image file.'}
    }


def test_create_predict_no_images(client, trained_images_ensemble,
                                  tmpdir, get_url):
    ensemble = trained_images_ensemble
    user = ensemble.user
    ufile = tmpdir.join('image.jpg')
    im = Image.new('RGB', (50, 50))
    im.save(str(ufile))
    ufile.name = 'image.jpg'
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': json.dumps([lm1_iter]),
        'file': ufile
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data, format='multipart')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': 'No images found.'
    }


def test_create_mrnn_predict_images(client, trained_mrnn_ensemble,
                                    get_url, tmpdir):
    ensemble = trained_mrnn_ensemble
    user = ensemble.user
    ufile = tmpdir.join('image.jpg')
    im = Image.new('RGB', (150, 150))
    im.save(str(ufile))
    ufile.name = 'image.jpg'
    lm1_iter = random.choice(
        ensemble.learn_models.all()[0].stats.all().values_list('id', flat=True)
    )
    lm2_iter = random.choice(
        ensemble.learn_models.all()[1].stats.all().values_list('id', flat=True)
    )
    data = {
        'iterations': json.dumps([lm1_iter, lm2_iter]),
        'file-0': ufile,
    }
    response = client.post(get_url('predict-list',
                                   params=[('key', user.apikey.key)]),
                           data=data,
                           format='multipart')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.content) == {
        'detail': ["This ensemble can't predict on files."]
    }
