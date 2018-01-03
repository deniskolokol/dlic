# coding: utf-8
import json
import random
import string
import pytest
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from web.models import ApiUser
from job.model_settings import (get_default_settings, CONV_LAYERS_CFG,
                                CONV_LAYER_PARAMS_CFG)
from job.models import LearnModel, JOB_STATE, TrainEnsemble, PredictEnsemble
from payments.models import Gift
from data_management.models import DataFile, DataSet
from rest_framework.test import APIClient


MRNN_PARAMS = {"maxnum_iter": 10, "h": 2, "f": 2, "cg_max_cg": 40,
               "cg_min_cg": 1, "lambda": 0.01, "mu": 0.001}
SPEARMINT = {
    "maxnum_iter": {"min": 20, "max": 20},
    "T": {"min": 20, "max": 85},
    "h": {"min": 2, "max": 100},
    "f": {"min": 2, "max": 100},
    "cg_max_cg": {"min": 40, "max": 200},
    "cg_min_cg": {"min": 1, "max": 30},
    "lambda": {"min": 0.01, "max": 1.0},
    "mu": {"min": 0.001, "max": 0.01}
}


class JClient(APIClient):

    def post_json(self, url, data, **kwds):
        return self.post(
            url,
            json.dumps(data),
            content_type='application/json',
            **kwds)


def earliest(qs, field='pk'):
    obj = qs._clone()
    obj.query.set_limits(high=1)
    obj.query.clear_ordering()
    obj.query.add_ordering('pk')
    return obj.get()


def register_user(name='test@example.com', file_format='TIMESERIES'):
    client = JClient()
    client.post(reverse('register'),
                data={'username': name, 'password': '123456', 'password_repeat': '123456',
                      'invite_code': settings.INVITE_KEYS[0]}, follow=True)
    client.login(username=name, password='123456')
    user = ApiUser.objects.filter(email=name)[0]
    prefix = ''.join([random.choice(string.digits + string.letters)
                      for i in range(0, 8)])
    s3file = DataFile.objects.create(
        user=user,
        key='uploads/' +
        prefix +
        '/test.txt')
    DataFile.objects.filter(pk=s3file.pk).update(file_format=file_format)
    ds = DataSet.objects.create(key='uploads/dataset/' + prefix + '/test.txt',
                                name='Data Set', data=s3file, user=s3file.user)
    return user, client, ds


def send_stats(learn_model, iteration=0, test_accuracy=0.9,
               test_loss=10, train_accuracy=0.9, time=10.5):
    client = JClient()
    s3_data = '/modeldata/' + \
        str(learn_model.id) + '/' + str(iteration) + '.json'
    return client.post_json(reverse('api_stats'),
                            data={'model': learn_model.id,
                                  'worker_key': settings.WORKER_KEY,
                                  'data': {'test_accuracy': test_accuracy,
                                           'test_loss': test_loss,
                                           'train_accuracy': train_accuracy,
                                           'iteration': iteration,
                                           'time': time},
                                  's3_data': s3_data,
                                  'queue_key': learn_model.ensemble.queue_key})


@pytest.mark.usefixtures('class_setup')
class RestartResume(TestCase):

    def setUp(self):
        self.user, self.client, self.ds = register_user()
        self.key = self.user.apikey.key

        client = JClient()
        model = LearnModel.MRNN
        ds2 = DataSet.objects.create(data=self.ds.data, filters=[],
                                     name='test.csv.zip', key='asd',
                                     user=self.ds.data.user)
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': ds2.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list')
                                    + '?key=' + self.key,
                                    data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TrainEnsemble.objects.count(), 1)
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': model,
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 10
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LearnModel.objects.count(), 10)
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        learn_model = LearnModel.objects.live()[0]
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)

        message = self.patch_queue['queue'][-1]
        self.body = {'ensemble': learn_model.ensemble.pk,
                     'sp_results': '',
                     'queue_key': learn_model.ensemble.queue_key,
                     'models': [],
                     'config': SPEARMINT.copy(),
                     'quantiles': None,
                     'options': {},
                     'data_type': 'TIMESERIES'}
        self.body['models'] = [
            {'id': m.pk, 'name': m.model_name,
             'model_params': m.model_params, 'out_nonlin': 'SOFTMAX'}
            for m in LearnModel.objects.live().order_by('pk')]

        self.body['train_dataset'] = \
            learn_model.ensemble.train_dataset.get_training_message()
        if learn_model.ensemble.test_dataset:
            self.body['test_dataset'] = \
                learn_model.ensemble.test_dataset.get_training_message()
        else:
            self.body['test_dataset'] = None
        if learn_model.ensemble.valid_dataset:
            self.body['valid_dataset'] = \
                learn_model.ensemble.valid_dataset.get_training_message()
        else:
            self.body['valid_dataset'] = None
        self.assertEqual(message, self.body)

    def send_stats(self, learn_model, iteration=0):
        response = send_stats(learn_model, iteration)
        self.assertEqual(response.status_code, 200)

    def resume_ensemble(self):
        client = JClient()
        ess = TrainEnsemble.objects
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        self.assertEqual(ess.get(pk=self.ensemble.pk).state,
                         TrainEnsemble.ST_QUEUE)
        return self.patch_queue['queue'][-1]

    def cancel_ensemble(self):
        client = JClient()
        ess = TrainEnsemble.objects
        response = client.post(reverse('ensemble-stop',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        ensemble = ess.get(pk=self.ensemble.pk)
        self.assertEqual(ensemble.state, ensemble.ST_STOP)
        self.patch_queue['queue'][-1]

    def test_restart_ensemble(self):
        ess = TrainEnsemble.objects
        client = JClient()
        # in queue cancel
        self.cancel_ensemble()
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        # worker to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        # cancel
        self.cancel_ensemble()
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['models'][0]['model_params'] = {'h': 1}
        for m in self.body['models']:
            m['model_params']['maxnum_iter'] = 45
        self.assertEqual(message, self.body)
        # worker to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        # send quantiles
        response = client.post_json(
            reverse('api_ensemble_status'),
            data={
                'ensemble': self.ensemble.id,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key,
                'quantiles': [
                    1,
                    2,
                    3,
                    4]})
        self.assertEqual(response.status_code, 200)
        ensemble = ess.get(pk=self.ensemble.pk)
        self.assertEqual(ensemble.quantiles, [1, 2, 3, 4])
        self.body['quantiles'] = [1, 2, 3, 4]
        for i in range(5):
            self.send_stats(learn_model, i)
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        self.assertEqual(learn_model.stats.live().count(), 5)
        # cancel
        self.cancel_ensemble()
        # resume with 5 iterations
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.latest(
            'iteration').s3_data
        self.body['models'][0]['high_score'] = 0.9
        self.body['models'][0]['lower_loss'] = 10
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        self.assertEqual(learn_model.stats.live().count(), 5)
        # cancel
        self.cancel_ensemble()
        # resume with 5 iterations from model resume
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().latest(
            'iteration').s3_data
        response = client.post(
            reverse('ensemble-resume', kwargs={'pk': self.ensemble.pk})
            + '?key=' + self.key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        # cancel
        self.cancel_ensemble()
        # resume with 3 iterations from model resume
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().get(
            iteration=2).s3_data
        response = client.post(
            reverse('model-resume', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key, data={'iteration': 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        _models_msg = self.body['models']
        self.body['models'] = [self.body['models'][0]]
        self.assertEqual(message, self.body)
        # assert other stats was removed
        self.assertEqual(learn_model.stats.count(), 5)
        self.assertEqual(learn_model.stats.live().count(), 3)
        self.assertEqual(range(3), list(learn_model.stats.live(
        ).order_by('iteration'
                   ).values_list('iteration', flat=True)))
        # worker first model to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(3, 10):
            self.send_stats(learn_model, i)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=learn_model.pk).state,
            JOB_STATE.FINISH)
        # ensemble in cancel state
        assert TrainEnsemble.objects.get(pk=self.ensemble.pk).state == \
            TrainEnsemble.ST_STOP
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['sp_results'] = 'just line\nand line\n'
        self.body['models'] = _models_msg
        self.body['models'].pop(0)
        self.assertEqual(message, self.body)
        # worker second model to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.exclude(
                state='FINISHED'))
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(6):
            self.send_stats(learn_model, i)
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        self.assertEqual(learn_model.stats.live().count(), 6)
        # cancel
        self.cancel_ensemble()
        # resume with 6 iterations
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().latest(
            'iteration').s3_data
        self.body['models'][0]['high_score'] = 0.9
        self.body['models'][0]['lower_loss'] = 10
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        # cancel
        self.cancel_ensemble()
        # resume with 6 iterations from model resume
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().latest(
            'iteration').s3_data
        response = client.post(
            reverse('ensemble-resume', kwargs={'pk': self.ensemble.pk})
            + '?key=' + self.key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        # cancel
        self.cancel_ensemble()
        # resume with 3 iterations from model resume
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().get(
            iteration=2).s3_data
        response = client.post(
            reverse('model-resume', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key, data={'iteration': 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        _models_msg = self.body['models']
        self.body['models'] = [self.body['models'][0]]
        self.assertEqual(message, self.body)
        # assert other stats was removed
        self.assertEqual(learn_model.stats.count(), 6)
        self.assertEqual(learn_model.stats.live().count(), 3)
        self.assertEqual(range(3), list(learn_model.stats.live(
        ).order_by('iteration'
                   ).values_list('iteration', flat=True)))
        # worker second model to train
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(3, 8):
            self.send_stats(learn_model, i)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\nfor second model\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=learn_model.pk).state,
            JOB_STATE.FINISH)
        self.assertEqual(learn_model.stats.count(), 11)
        self.assertEqual(learn_model.stats.live().count(), 8)
        self.assertEqual(range(8), list(learn_model.stats.live(
        ).order_by('iteration'
                   ).values_list('iteration', flat=True)))
        assert TrainEnsemble.objects.get(pk=self.ensemble.pk).state == \
            TrainEnsemble.ST_STOP
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['models'] = _models_msg
        self.body['models'].pop(0)
        self.body['sp_results'] = 'just line\nand line\njust line\nand ' \
                                  'line\nfor second model\n'
        self.assertEqual(message, self.body)
        # worker third model to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.exclude(
                state='FINISHED'))
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(6):
            self.send_stats(learn_model, i)
        learn_model3 = LearnModel.objects.get(pk=learn_model.pk)
        self.assertEqual(learn_model3.stats.live().count(), 6)
        # cancel
        self.cancel_ensemble()
        # now we want resume first model from iteration 5
        # third model should save all stats and resume from last
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model3.stats.live().latest(
            'iteration').s3_data
        self.body['models'][0]['high_score'] = 0.9
        self.body['models'][0]['lower_loss'] = 10
        learn_model = LearnModel.objects.live().order_by('pk')[0]
        temp = {'id': learn_model.pk, 'name': learn_model.model_name,
                'model_params': learn_model.model_params, 'resume': True,
                'resume_X': learn_model.stats.live().get(iteration=5).s3_data,
                'out_nonlin': 'SOFTMAX', 'high_score': 0.9,
                'lower_loss': 10}
        self.body['models'].insert(0, temp)
        self.body['sp_results'] = 'just line\nand line\nfor second model\n'
        response = client.post(
            reverse('model-resume', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key, data={'iteration': 5}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        _models_msg = self.body['models']
        self.body['models'] = [self.body['models'][0]]
        self.assertEqual(message, self.body)
        # assert other stats was removed
        self.assertEqual(learn_model.stats.count(), 12)
        self.assertEqual(learn_model.stats.live().count(), 6)
        self.assertEqual(range(6), list(learn_model.stats.live(
        ).order_by('iteration'
                   ).values_list('iteration', flat=True)))
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        self.assertEqual(learn_model.state, 'QUEUE')
        # cancel
        self.cancel_ensemble()
        data = {
            'train_dataset': self.ensemble.train_dataset.id,
            'test_dataset': self.ensemble.test_dataset.id
        }
        response = client.put(reverse('ensemble-detail',
                                      kwargs={'pk': self.ensemble.pk}) +
                              '?key=' + self.ensemble.user.apikey.key,
                              data=data, format='json')
        self.assertEqual(response.status_code, 200)
        response = client.post(
            reverse('model-resume', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key, data={'iteration': 3}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        self.assertEqual(learn_model.stats.count(), 12)
        self.assertEqual(learn_model.stats.live().count(), 4)
        assert range(4) == list(learn_model.stats.live().order_by('iteration')
                                .values_list('iteration', flat=True))
        message = self.patch_queue['queue'][-1]
        self.body['models'] = self.body['models'][:1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['models'][0]['resume_X'] = learn_model.stats.live().get(
            iteration=3).s3_data
        self.maxDiff = None
        #self.body['file_name'] = self.ds.key
        self.body['quantiles'] = ess.get(pk=self.ensemble.pk).quantiles
        self.assertEqual(len(message.keys()), len(self.body.keys()))
        self.assertEqual(message, self.body)
        # cancel
        self.cancel_ensemble()
        # restart model
        response = client.post(
            reverse('model-restart', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ess.get(
                pk=self.ensemble.pk).state,
            TrainEnsemble.ST_QUEUE)
        self.assertEqual(learn_model.stats.count(), 12)
        self.assertEqual(learn_model.stats.live().count(), 0)
        self.assertEqual(range(0), list(learn_model.stats.live().values_list(
            'iteration', flat=True)))
        message = self.patch_queue['queue'][-1]
        del self.body['models'][0]['resume']
        del self.body['models'][0]['resume_X']
        del self.body['models'][0]['high_score']
        del self.body['models'][0]['lower_loss']
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)

    def test_delete_model(self):
        ess = TrainEnsemble.objects
        client = JClient()
        # in queue
        self.assertEqual(self.ensemble.learn_models.live().count(), 10)
        self.assertEqual(self.ensemble.learn_models.count(), 10)
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': learn_model.id})
                                 + '?key=' + self.key)
        self.assertEqual(response.status_code, 400)
        assert 'Model in state: QUEUE. Can\'t be deleted' == \
            json.loads(response.content)['detail']['problem']
        self.assertEqual(self.ensemble.learn_models.live().count(), 10)
        # cancel
        self.cancel_ensemble()
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': learn_model.id})
                                 + '?key=' + self.key)
        assert response.status_code == 204
        self.assertEqual(self.ensemble.learn_models.live().count(), 9)
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['models'].pop(0)
        self.assertEqual(message, self.body)
        # cancel
        self.cancel_ensemble()
        self.assertEqual(self.ensemble.learn_models.live().count(), 9)
        # resume
        message = self.resume_ensemble()
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.assertEqual(message, self.body)
        # worker to train
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': learn_model.id})
                                 + '?key=' + self.key)
        assert response.status_code == 400
        assert 'Model in state: TRAIN. Can\'t be deleted' == \
            json.loads(response.content)['detail']['problem']
        self.assertEqual(self.ensemble.learn_models.live().count(), 9)
        for i in range(1, 6):
            self.send_stats(learn_model, i)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LearnModel.objects.get(pk=learn_model.pk).state,
                         JOB_STATE.FINISH)
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': learn_model.id})
                                 + '?key=' + self.key)
        assert response.status_code == 204
        self.assertEqual(self.ensemble.learn_models.live().count(), 8)
        self.assertEqual(self.ensemble.learn_models.count(), 10)
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': learn_model.id})
                                 + '?key=' + self.key)
        self.assertEqual(response.status_code, 404)

    def test_training_time(self):
        ess = TrainEnsemble.objects
        client = JClient()
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(5):  # 10.5 seconds
            self.send_stats(learn_model, i)
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        self.assertEqual(learn_model.stats.live().count(), 5)
        response = client.get(reverse('model-detail',
                                      kwargs={'pk': learn_model.id})
                              + '?key=' + self.key)
        assert json.loads(response.content)['training_time'] == 52.5
        # cancel
        self.cancel_ensemble()
        # resume with 3 iterations from model resume
        self.body['models'][0]['model_params'] = {'h': 1}
        self.body['models'][0]['resume'] = True
        self.body['models'][0]['resume_X'] = learn_model.stats.live().get(
            iteration=2).s3_data
        self.body['models'][0]['high_score'] = 0.9
        self.body['models'][0]['lower_loss'] = 10
        for m in self.body['models']:
            m['model_params']['maxnum_iter'] = 45
        response = client.post(
            reverse('model-resume', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key, data={'iteration': 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ess.get(pk=self.ensemble.pk).state,
                         TrainEnsemble.ST_QUEUE)
        message = self.patch_queue['queue'][-1]
        self.body['queue_key'] = ess.get(pk=self.ensemble.pk).queue_key
        self.body['models'] = [self.body['models'][0]]
        self.assertEqual(message, self.body)
        lm_url = reverse('model-detail', kwargs={'pk': learn_model.pk}) \
            + '?key=' + self.key
        response = client.get(lm_url)
        assert json.loads(response.content)['training_time'] == 52.5
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live())
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(3, 8):  # 10.5 seconds
            self.send_stats(learn_model, i)
        response = client.get(lm_url)
        assert json.loads(response.content)['training_time'] == 105.
        # finish 1 model
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        # 10.5 * 10
        response = client.get(lm_url)
        assert json.loads(response.content)['training_time'] == 105.
        ens_url = reverse('ensemble-detail', kwargs={'pk': self.ensemble.pk}) \
            + '?key=' + self.key
        response = client.get(ens_url)
        assert json.loads(response.content)['total_time'] == 105.
        lm1 = learn_model
        # second model
        learn_model = earliest(
            ess.get(
                pk=self.ensemble.pk).learn_models.live().exclude(
                state='FINISHED'))
        response = client.post(
            reverse('model-restart', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key
        )
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        assert response.status_code == 200
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        assert response.status_code == 200
        for i in range(7):  # 10.5 seconds
            self.send_stats(learn_model, i)
        lm2_url = reverse('model-detail', kwargs={'pk': learn_model.pk}) + \
            '?key=' + self.key
        response = client.get(lm2_url)
        assert json.loads(response.content)['training_time'] == 73.5
        response = client.get(ens_url)
        assert json.loads(response.content)['total_time'] == 105. + 73.5
        # delete 1 model
        self.cancel_ensemble()
        response = client.delete(reverse('model-detail',
                                         kwargs={'pk': lm1.id})
                                 + '?key=' + self.key)
        assert response.status_code == 204
        response = client.get(lm2_url)
        assert json.loads(response.content)['training_time'] == 73.5
        response = client.get(ens_url)
        assert json.loads(response.content)['total_time'] == 105. + 73.5


class StatusTest(TestCase):

    def setUp(self):
        self.user, self.client, self.ds = register_user()
        self.key = self.user.apikey.key

    def test_ensemble_status(self):
        client = JClient()
        # NEW
        ds2 = DataSet.objects.create(data=self.ds.data, filters=[],
                                     name='test.csv.zip', key='asd',
                                     user=self.ds.user)
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': ds2.pk,
            'out_nonlin': 'SOFTMAX'
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key,
                                    data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TrainEnsemble.objects.count(), 1)
        ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': ensemble.id,
                'model_params': {'maxnum_iter': 45},
            }, {
                'ensemble': ensemble.id,
                'model_params': {'maxnum_iter': 45},
            }
        ]
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LearnModel.objects.count(), 2)
        pk1, pk2 = LearnModel.objects.live().values_list('pk', flat=True)
        learn_model = LearnModel.objects.get(pk=pk1)
        epk = ensemble.pk
        self.assertEqual(learn_model.state, JOB_STATE.NEW)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_NEW)
        ens = TrainEnsemble.objects
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # QUEUE
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        learn_model = LearnModel.objects.get(pk=pk1)
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_QUEUE)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # TRAIN
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_TRAIN)
        self.assertEqual(LearnModel.objects.get(pk=pk1).state, JOB_STATE.TRAIN)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # ERROR
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.ERROR,
                'error': 'some error',
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_ERROR)
        self.assertFalse(TrainEnsemble.objects.get(pk=ensemble.id).canceled)
        self.assertEqual(LearnModel.objects.get(pk=pk1).state, JOB_STATE.ERROR)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk2).state,
            JOB_STATE.CANCEL)
        self.assertEqual(ens.on_worker().count(), 0)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 1)
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        self.assertEqual(LearnModel.objects.get(pk=pk1).state, JOB_STATE.QUEUE)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_QUEUE)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # CANCEL
        response = client.post(reverse('ensemble-stop',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_STOP)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk1).state,
            JOB_STATE.CANCEL)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk2).state,
            JOB_STATE.CANCEL)
        self.assertTrue(TrainEnsemble.objects.get(pk=ensemble.id).canceled)
        self.assertEqual(ens.on_worker().count(), 0)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 1)
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        self.assertEqual(LearnModel.objects.get(pk=pk1).state, JOB_STATE.QUEUE)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_QUEUE)
        self.assertFalse(TrainEnsemble.objects.get(pk=ensemble.id).canceled)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        learn_model = LearnModel.objects.get(pk=pk1)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_TRAIN)
        self.assertEqual(LearnModel.objects.get(pk=pk1).state, JOB_STATE.TRAIN)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # FINISH
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk1).state,
            JOB_STATE.FINISH)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_TRAIN)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # TRAIN
        learn_model = LearnModel.objects.get(pk=pk2)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_TRAIN)
        self.assertEqual(LearnModel.objects.get(pk=pk2).state, JOB_STATE.TRAIN)
        self.assertEqual(ens.on_worker().count(), 1)
        self.assertEqual(ens.finished().count(), 0)
        self.assertEqual(ens.canceled().count(), 0)
        # FINISH
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk2).state,
            JOB_STATE.FINISH)
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_FINISH)
        #
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 400
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_FINISH)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk1).state,
            JOB_STATE.FINISH)
        self.assertEqual(
            LearnModel.objects.get(
                pk=pk2).state,
            JOB_STATE.FINISH)
        self.assertEqual(ens.on_worker().count(), 0)
        self.assertEqual(ens.finished().count(), 1)
        self.assertEqual(ens.canceled().count(), 0)
        lm1, lm2 = ens.finished()[0].learn_models.live().values_list(
            'id', flat=True)
        response = client.delete(reverse('model-detail', kwargs={'pk': lm1})
                                 + '?key=' + self.key)
        assert response.status_code == 204
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_FINISH)
        response = client.delete(reverse('model-detail', kwargs={'pk': lm2})
                                 + '?key=' + self.key)
        assert response.status_code == 204
        self.assertEqual(TrainEnsemble.objects.get(pk=epk).state,
                         TrainEnsemble.ST_EMPTY)


@pytest.mark.usefixtures('class_setup')
class ApiTest(TestCase):

    def setUp(self):
        self.user, self.client, self.ds = register_user()
        self.key = self.user.apikey.key

    def test_train(self):
        client = JClient()
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'auto_next_model': True,
            'out_nonlin': 'SOFTMAX',
        }
        response = client.post(reverse('ensemble-list')
                               + '?key=' + self.user.apikey.key,
                               data=data, format='json')
        assert response.status_code == 201
        ensemble_id = json.loads(response.content)['id']
        data = {
            'ensemble': ensemble_id,
            'model_name': 'MRNN',
            'model_params': {'maxnum_iter': 10}
        }
        for _ in range(10):
            response = client.post(reverse('model-list')
                                   + '?key=' + self.user.apikey.key,
                                   data=data, format='json')
            assert response.status_code == 201
        self.assertEqual(TrainEnsemble.objects.count(), 1)
        self.assertEqual(LearnModel.objects.count(), 10)
        learn_model = LearnModel.objects.live()[0]
        self.assertEqual(learn_model.state, JOB_STATE.NEW)
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble_id})
                               + '?key=' + self.user.apikey.key)
        assert response.status_code == 200
        learn_model = LearnModel.objects.live()[0]
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)

        message = self.patch_queue['queue'][-1]
        body = {'ensemble': learn_model.ensemble.pk,
                'sp_results': '',
                'queue_key': learn_model.ensemble.queue_key,
                'models': [],
                'config': SPEARMINT.copy(),
                'quantiles': None,
                'options': {},
                'data_type': 'TIMESERIES'}
        body['models'] = [{'id': m.pk, 'name': m.model_name,
                           'model_params': m.model_params,
                           'out_nonlin': 'SOFTMAX'}
                          for m in LearnModel.objects.live().order_by('pk')]
        body['train_dataset'] = \
            learn_model.ensemble.train_dataset.get_training_message()
        body['test_dataset'] = \
            learn_model.ensemble.test_dataset.get_training_message()
        body['valid_dataset'] = None
        self.assertEqual(message, body)

        # test s3
        df = DataFile.objects.create(user=self.user, key='uploads/test3.txt')
        df.meta = {'key': 'uploads/test3.txt', 'version': 3,
                   'size': 4, 'data_type': 'TIMESERIES'}
        df.file_format = 'TIMESERIES'
        df.save()
        dataset = DataSet.objects.create(
            data=df, name='Ds 1', key='datasets/' + df.key, user=df.user
        )
        data = {
            'train_dataset': dataset.pk,
            'test_dataset': dataset.pk,
            'auto_next_model': True,
            'out_nonlin': 'SOFTMAX',
        }
        response = client.post(reverse('ensemble-list')
                               + '?key=' + self.user.apikey.key,
                               data=data, format='json')
        assert response.status_code == 201
        ensemble_id = json.loads(response.content)['id']
        data = {
            'ensemble': ensemble_id,
            'model_name': 'MRNN',
            'model_params': {'maxnum_iter': 10}
        }
        for _ in range(10):
            response = client.post(reverse('model-list')
                                   + '?key=' + self.user.apikey.key,
                                   data=data, format='json')
            assert response.status_code == 201
        self.assertEqual(LearnModel.objects.count(), 20)
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': ensemble_id})
                               + '?key=' + self.user.apikey.key)
        assert response.status_code == 200
        ensemble = TrainEnsemble.objects.get(train_dataset=dataset.pk)
        learn_model = LearnModel.objects.live().order_by('-created')[0]
        assert ensemble.learn_models.live()[0].state == JOB_STATE.QUEUE
        message = self.patch_queue['queue'][-1]
        body = {'ensemble': ensemble.pk,
                'sp_results': '',
                'queue_key': ensemble.queue_key,
                'models': [],
                'config': SPEARMINT.copy(),
                'quantiles': None,
                'options': {},
                'data_type': 'TIMESERIES'}
        body['models'] = [{'id': m.pk, 'name': m.model_name,
                           'model_params': m.model_params,
                           'out_nonlin': 'SOFTMAX'}
                          for m in ensemble.learn_models.live().order_by('pk')]
        body['train_dataset'] = \
            learn_model.ensemble.train_dataset.get_training_message()
        body['test_dataset'] = \
            learn_model.ensemble.test_dataset.get_training_message()
        body['valid_dataset'] = None
        assert message == body

        response = client.post(reverse('register'),
                               data={
                                   'username': 'test2@example.com',
                                   'password': '123456',
                                   'invite_code': settings.INVITE_KEYS[0]},
                               follow=True)
        user = ApiUser.objects.exclude(pk=self.user.pk)[0]
        df2 = DataFile.objects.create(user=user, key='uploads/test2.txt')
        dataset2 = DataSet.objects.create(
            key='datasets/' + df2.key, name='Data Set', data=df2, user=df2.user
        )
        data = {
            'train_dataset': dataset.pk,
            'test_dataset': dataset2.pk,
            'auto_next_model': True,
            'out_nonlin': 'SOFTMAX',
        }
        response = client.post(reverse('ensemble-list')
                               + '?key=' + self.user.apikey.key,
                               data=data, format='json')
        assert response.status_code == 400
        assert json.loads(response.content) == {
            "test_dataset": ["Invalid pk '3' - object does not exist."]
        }


class WorkerApiTest(TestCase):

    def setUp(self):
        self.user, self.client, self.ds = register_user()
        self.key = self.user.apikey.key

    def test_worker_key(self):
        client = JClient()
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list')
                                    + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201
        assert TrainEnsemble.objects.count() == 1
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'MRNN',
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 10
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201
        response = client.post_json(reverse('api_train_status'), data={})
        self.assertEqual(response.status_code, 403)
        self.assertTrue('invalid worker key' in response.content)
        response = client.post_json(reverse('api_stats'), data={})
        self.assertEqual(response.status_code, 403)
        self.assertTrue('invalid worker key' in response.content)
        response = client.post_json(reverse('api_ensemble_status'), data={})
        self.assertEqual(response.status_code, 403)
        self.assertTrue('invalid worker key' in response.content)
        response = client.post_json(reverse('api_predict_ensemble_status'),
                                    data={})
        self.assertEqual(response.status_code, 403)
        self.assertTrue('invalid worker key' in response.content)

    def test_api_forms(self):
        client = JClient()
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 201
        assert TrainEnsemble.objects.count() == 1
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'MRNN',
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 10
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201
        self.assertEqual(LearnModel.objects.count(), 10)
        ensemble = TrainEnsemble.objects.all()[0]
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        learn_model = LearnModel.objects.live()[0]
        ensemble = learn_model.ensemble
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)
        # test to TRAIN state
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY})
        self.assertEqual(response.status_code, 400)
        self.assertTrue("queue_key" in response.content)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': 'random'})
        self.assertEqual(response.status_code, 400)
        self.assertTrue("Queue key doesn't match" in response.content)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)

        # test stats
        response = client.post_json(
            reverse('api_stats'),
            data={
                'model': learn_model.id,
                'worker_key': settings.WORKER_KEY,
                'data': {
                    'status': 'run',
                    'data': [
                        0,
                        1,
                        2]}})
        self.assertEqual(response.status_code, 400)
        response = client.post_json(
            reverse('api_stats'),
            data={
                'model': learn_model.id,
                'worker_key': settings.WORKER_KEY,
                'data': {
                    'status': 'run',
                    'data': [
                        0,
                        1,
                        2]},
                's3_data': '/modeldata/' +
                str(
                    learn_model.id) +
                '/1.json',
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 400)

        # test to FINISH state
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'worker_key': settings.WORKER_KEY,
                'queue_key': 'random'})
        self.assertEqual(response.status_code, 400)
        self.assertTrue("Queue key doesn't match" in response.content)
        response = client.post_json(reverse('api_train_status'),
                                    data={
                                        'model': learn_model.id,
                                        'state': JOB_STATE.FINISH,
                                        'sp_results': 'just line\nand line\n',
                                        'worker_key': settings.WORKER_KEY,
                                        'queue_key': ensemble.queue_key})
        self.assertEqual(response.status_code, 400)
        assert 'should set sp_results' in response.content
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'detailed_results': 'just line\nand line\n',
                'worker_key': settings.WORKER_KEY,
                'queue_key': ensemble.queue_key})
        self.assertEqual(response.status_code, 400)
        self.assertTrue('should set sp_results' in response.content)

    def test_worker_api(self):
        client = JClient()
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 201
        assert TrainEnsemble.objects.count() == 1
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'MRNN',
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 10
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201
        self.assertEqual(LearnModel.objects.count(), 10)
        jobs = LearnModel.objects
        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        assert response.status_code == 200
        learn_model = jobs.all()[0]
        # test state change to TRAIN
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(jobs.get(pk=learn_model.pk).state, JOB_STATE.TRAIN)

        # test stats
        data = {'model': learn_model.id,
                'worker_key': settings.WORKER_KEY,
                'data': {'test_accuracy': 0.9,
                         'train_accuracy': 0.9,
                         'iteration': 1,
                         'time': 10},
                's3_data': '/modeldata/' + str(learn_model.id) + '/1.json',
                'queue_key': learn_model.ensemble.queue_key}
        response = client.post_json(reverse('api_stats'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(learn_model.stats.live()[0].data, {
            'test_accuracy': 0.9,
            'train_accuracy': 0.9,
            'iteration': 1,
            'time': 10
        })
        data = {'model': learn_model.id,
                'worker_key': settings.WORKER_KEY,
                'data': {'test_accuracy': 0.9,
                         'train_accuracy': 0.9,
                         'iteration': 1,
                         'time': 15},
                's3_data': '/modeldata/' + str(learn_model.id) + '/1.json',
                'queue_key': learn_model.ensemble.queue_key}
        response = client.post_json(reverse('api_stats'), data=data)
        self.assertEqual(response.status_code, 200)
        data = {'model': learn_model.id,
                'worker_key': settings.WORKER_KEY,
                'data': {'test_accuracy': 0.9,
                         'train_accuracy': 0.9,
                         'iteration': 1,
                         'time': 16.5},
                's3_data': '/modeldata/' + str(learn_model.id) + '/1.json',
                'queue_key': learn_model.ensemble.queue_key}
        response = client.post_json(reverse('api_stats'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(learn_model.stats.live().count(), 3)

        # test state change to FINISH
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(jobs.get(pk=learn_model.pk).state, JOB_STATE.FINISH)
        # test state change to ERROR
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.ERROR,
                'error': 'some error',
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(jobs.get(pk=learn_model.pk).state, JOB_STATE.FINISH)
        learn_model = jobs.get(pk=learn_model.pk)
        learn_model.state = JOB_STATE.TRAIN
        learn_model.save()
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.ERROR,
                'error': 'some error',
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(jobs.get(pk=learn_model.pk).state, JOB_STATE.ERROR)

        # test ensemble state change to ERROR
        ensemble = TrainEnsemble.objects.get(pk=learn_model.ensemble.pk)
        self.assertEqual(ensemble.state, TrainEnsemble.ST_ERROR)
        learn_model.state = JOB_STATE.TRAIN
        learn_model.save()
        ensemble.state = ensemble.ST_TRAIN
        ensemble.save()
        response = client.post_json(
            reverse('api_ensemble_status'),
            data={
                'ensemble': ensemble.pk,
                'traceback': 'traceback info',
                'error': 'some error',
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        ensemble = TrainEnsemble.objects.get(pk=ensemble.pk)
        self.assertEqual(ensemble.error, 'some error')
        self.assertEqual(ensemble.traceback, 'traceback info')
        self.assertEqual(ensemble.state, TrainEnsemble.ST_ERROR)


@pytest.mark.usefixtures('class_setup')
class Billing(TestCase):

    def setUp(self):
        self.user, self.client, self.ds = register_user()
        self.key = self.user.apikey.key

    def test_require_billing(self):
        client = JClient()
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 201
        assert TrainEnsemble.objects.count() == 1
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'MRNN',
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 10
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201

        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.user.apikey.key)
        assert response.status_code == 200
        ensemble = TrainEnsemble.objects.all()[0]
        learn_model = earliest(
            TrainEnsemble.objects.get(pk=ensemble.pk).learn_models.live()
        )
        # start train
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        response = send_stats(learn_model, iteration=0, time=13700)
        self.assertEqual(response.status_code, 403)

        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 403
        assert 'You do not have paid time. Purchase time to continue' in \
            response.content
        self.assertEqual(TrainEnsemble.objects.count(), 1)

    def test_time_tracking(self):
        client = JClient()
        Gift.objects.create(user=self.user, minutes=9999)
        data = {
            'train_dataset': self.ds.pk,
            'test_dataset': self.ds.pk,
            'out_nonlin': 'SOFTMAX',
            'auto_next_model': True
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 201
        assert TrainEnsemble.objects.count() == 1
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'MRNN',
                'model_params': {'maxnum_iter': 45},
            }
        ]
        data *= 2
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201

        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.user.apikey.key)
        assert response.status_code == 200
        ensemble = TrainEnsemble.objects.all()[0]
        learn_model = earliest(TrainEnsemble.objects.get(pk=ensemble.pk
                                                         ).learn_models.live())
        # start train
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        response = send_stats(learn_model, iteration=0, time=55)
        self.assertEqual(response.status_code, 200)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertEqual(user.seconds_spent, 55)
        self.assertEqual(user.minutes_spent, 1)
        response = send_stats(learn_model, iteration=1, time=5.52)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 60.52)
        self.assertEqual(user.minutes_spent, 2)
        # cancel
        response = client.post(reverse('ensemble-stop',
                                       kwargs={'pk': ensemble.pk})
                               + '?key=' + self.key)
        # restart
        response = client.post(
            reverse('model-restart', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key
        )
        self.assertEqual(response.status_code, 200)
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        response = send_stats(learn_model, iteration=0, time=70)
        self.assertEqual(response.status_code, 200)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 130.52)
        self.assertEqual(user.minutes_spent, 3)
        for i in range(1, 10):
            response = send_stats(learn_model, i, time=60)
            self.assertEqual(response.status_code, 200)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 130.52 + 60 * 9)
        # finish
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LearnModel.objects.get(pk=learn_model.pk).state,
                         JOB_STATE.FINISH)
        #####
        # second model
        lms = TrainEnsemble.objects.get(pk=ensemble.pk) \
            .learn_models.live().exclude(state='FINISHED')
        learn_model = earliest(lms)
        response = client.post(
            reverse('model-restart', kwargs={'pk': learn_model.pk})
            + '?key=' + self.key
        )
        assert response.status_code == 200
        # start train
        learn_model = LearnModel.objects.get(pk=learn_model.pk)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(0, 5):
            response = send_stats(learn_model, i, time=60)
            self.assertEqual(response.status_code, 200)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 300 + 130.52 + 60 * 9)
        # finish
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LearnModel.objects.get(pk=learn_model.pk).state,
                         JOB_STATE.FINISH)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 300 + 130.52 + 60 * 9)
        # PREDICT
        models = TrainEnsemble.objects.get(pk=ensemble.pk).learn_models.live()
        iterations = [x.stats.all().latest('id').pk for x in models]
        data = {
            'input_data': '1,2',
            'iterations': iterations
        }
        response = client.post(reverse('predict-list') + '?key=' + self.key,
                               data=data, format='json')
        self.assertEqual(response.status_code, 201)
        ensemble = PredictEnsemble.objects.all()[0]
        data = {'ensemble': ensemble.pk,
                'queue_key': ensemble.queue_key,
                'time': 33,
                'results': {
                    'avg_results': '',
                    'avg_pre_activation_results': '',
                    'predicts': ''
                },
                'worker_key': settings.WORKER_KEY
                }
        response = client.post_json(reverse('api_predict_ensemble_status'),
                                    data=data)
        self.assertEqual(response.status_code, 200)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertAlmostEqual(user.seconds_spent, 300 + 130.52 + 60 * 9 + 33)


@pytest.mark.usefixtures('class_setup')
class SharedModels(TestCase):

    def setUp(self):
        self.user, self.client, self.dataset = register_user()
        self.s3file = self.dataset.data
        self.key = self.user.apikey.key
        self.s3file.meta = {
            'key': 'uploads/test3.txt', 'version': 3,
            'size': 4, 'data_type': 'IMAGES',
            'classes': {'class1': 2, 'class2': 3}
        }
        self.s3file.file_format = 'IMAGES'
        self.s3file.save()
        self.assertEqual(DataFile.objects.get(pk=self.s3file.pk).file_format,
                         'IMAGES')

        client = JClient()
        data = {
            'train_dataset': self.dataset.pk,
            'test_dataset': self.dataset.pk,
        }
        response = client.post_json(reverse('ensemble-list') +
                                    '?key=' + self.key, data=data)
        assert response.status_code == 201
        self.ensemble = TrainEnsemble.objects.all()[0]
        data = [
            {
                'ensemble': self.ensemble.id,
                'model_name': 'CONV',
                'model_params': {
                    'img_size': 64,
                    'maxnum_iter': 10,
                    'dropout': 0.5,
                    'random_sparse': True
                },
            }
        ]
        data *= 2
        response = client.post_json(reverse('model-list') + '?key=' + self.key,
                                    data=data)
        assert response.status_code == 201

        response = client.post(reverse('ensemble-resume',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.user.apikey.key)
        assert response.status_code == 200
        self.assertEqual(TrainEnsemble.objects.count(), 1)
        self.ensemble = TrainEnsemble.objects.all()[0]
        self.assertEqual(LearnModel.objects.count(), 2)
        learn_model = LearnModel.objects.live()[0]
        self.assertEqual(learn_model.state, JOB_STATE.QUEUE)
        message = self.patch_queue['queue'][-1]
        outputs = \
            learn_model.ensemble.train_dataset.data.get_cifar_outputs_num()
        self.body = {'ensemble': learn_model.ensemble.pk,
                     'sp_results': '',
                     'queue_key': learn_model.ensemble.queue_key,
                     'models': [],
                     'config': None,
                     'quantiles': None,
                     'options': {
                     },
                     'data_type': 'IMAGES',
                     }

        self.body['final_output'] = outputs
        #FIXME: wtf is SOFTMAX doing in data_type == IMAGES
        self.body['models'] = [
            {'id': m.pk, 'name': m.model_name,
             'model_params': m.model_params, 'out_nonlin': 'SOFTMAX'}
            for m in LearnModel.objects.live().order_by('pk')]

        self.body['train_dataset'] = \
            learn_model.ensemble.train_dataset.get_training_message()
        self.body['test_dataset'] = \
            learn_model.ensemble.test_dataset.get_training_message()
        self.body['valid_dataset'] = None
        assert message == self.body

    def test_share(self):
        client = JClient()
        learn_model = LearnModel.objects.live()[0]
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(3, 10):
            send_stats(learn_model, i)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=learn_model.pk).state,
            JOB_STATE.FINISH)
        learn_model = LearnModel.objects.live().exclude(state='FINISHED')[0]
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.TRAIN,
                'worker_key': settings.WORKER_KEY,
                'model_params': {
                    'test': 1,
                    'h': 1},
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        for i in range(3, 10):
            send_stats(learn_model, i)
        response = client.post_json(
            reverse('api_train_status'),
            data={
                'model': learn_model.id,
                'state': JOB_STATE.FINISH,
                'sp_results': 'just line\nand line\n',
                'detailed_results': 'file\nwith training\nstats\n' * 10,
                'worker_key': settings.WORKER_KEY,
                'queue_key': learn_model.ensemble.queue_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LearnModel.objects.get(
                pk=learn_model.pk).state,
            JOB_STATE.FINISH)
        self.assertEqual(TrainEnsemble.objects.all()[0].state,
                         TrainEnsemble.ST_FINISH)

        user2, client2, dataset2 = register_user(name='t@t.com')
        # using client2 (user2 logged in) without key
        response = client2.get(
            reverse(
                'view_train_ensemble',
                kwargs={
                    'pk': self.ensemble.pk}),
            follow=True)
        self.assertEqual(response.status_code, 404)
        response = client.post(reverse('ensemble-share',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        self.assertEqual(response.status_code, 403)
        self.user.is_superuser = True
        self.user.save()
        response = client.post(reverse('ensemble-share',
                                       kwargs={'pk': self.ensemble.pk})
                               + '?key=' + self.key)
        self.assertEqual(response.status_code, 200)

        response = client2.get(
            reverse(
                'view_train_ensemble',
                kwargs={
                    'pk': self.ensemble.pk}),
            follow=True)
        self.assertEqual(response.status_code, 200)
        response = client.post(
            reverse('model-restart', kwargs={'pk': learn_model.pk})
            + '?key=' + user2.apikey.key
        )
        self.assertEqual(response.status_code, 403)

        model_params = get_default_settings('CONV')
        model_params['maxnum_iter'] = 100
        response = client2.put(
            reverse('model-detail', kwargs={'pk': learn_model.pk}),
            data={'model_params': model_params}
        )
        self.assertEqual(response.status_code, 403)

        response = client2.put(reverse('ensemble-detail',
                                       kwargs={'pk': self.ensemble.pk}),
                               data={'auto_next_model': False,
                                     'train_dataset': dataset2.pk})
        self.assertEqual(response.status_code, 403)

        response = client2.delete(reverse('model-detail',
                                          kwargs={'pk': learn_model.id}))
        self.assertEqual(response.status_code, 403)

        response = client2.delete(
            reverse(
                'data-detail',
                kwargs={
                    'pk': self.ensemble.train_dataset.pk}))
        self.assertEqual(response.status_code, 403)
        response = client2.delete(
            reverse('ensemble-detail',
                    kwargs={'pk': self.ensemble.pk})
        )
        self.assertEqual(response.status_code, 403)
