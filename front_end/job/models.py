import os
import random
import string
import logging
import json
from collections import namedtuple, OrderedDict
from hashlib import sha1
from django.db import models
from django.db.models import Q, Sum, F
from django.db.models.query import QuerySet
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site
from jsonfield import JSONField
from core.models import CustomManager
from core.utils import deep_update
from web.models import ApiUser
from job.messaging import queue_job, get_queue_size
from job.model_settings import (get_default_settings, CONV_LAYERS_CFG,
                                CONV_LAYER_PARAMS_CFG)
from data_management.models import DataSet
from job.hyperparams import hyperparams as hp
from job.exceptions import BadOperation

JobState = namedtuple(
    'JobState', 'NEW QUEUE TRAIN PREDICT ERROR FINISH CANCEL RESUME DELETE'
)

JOB_STATE = JobState(NEW='NEW', QUEUE='QUEUE', TRAIN='TRAIN',
                     PREDICT='PREDICT', ERROR='ERROR', FINISH='FINISHED',
                     CANCEL='CANCELED', RESUME='RESUME', DELETE='DELETED')

GENERAL_STATES = (
    (JOB_STATE.NEW, 'new'),
    (JOB_STATE.QUEUE, 'in queue'),
    (JOB_STATE.ERROR, 'error'),
    (JOB_STATE.FINISH, 'finished'),
)


logger = logging.getLogger(__name__)


class TrainEnsembleQuerySet(QuerySet):
    def live(self):
        return self.exclude(deleted=True)

    def on_worker(self):
        return self.live().filter(
            Q(learn_models__state__in=('TRAIN', 'NEW', 'QUEUE')) &
            (Q(error__isnull=True) | Q(error=''))
        ).distinct().order_by('-pk')

    def finished(self):
        lms = LearnModel.objects.live().exclude(state='FINISHED')
        return self.live().exclude(learn_models__in=lms) \
            .distinct().order_by('-pk')

    def canceled(self):
        return self.live().filter(
            Q(learn_models__state__in=('ERROR', 'CANCELED')) |
            (~Q(error__isnull=True) & ~Q(error=''))
        ).distinct().order_by('-pk')

    def visible_to(self, user):
        return self.live().filter(Q(user=user) | Q(shared=True))

    def for_serialization(self):
        subselect = ("SELECT COUNT(*) from job_learnmodel "
                     "where job_learnmodel.ensemble_id = job_trainensemble.id "
                     "and job_learnmodel.state != 'DELETED'")
        return self.annotate(total_time=Sum('learn_models__training_time'))\
            .extra(select={'models_count': subselect})\
            .select_related('train_dataset', 'test_dataset')\
            .only('id', 'shared', 'created', 'train_dataset__id',
                  'test_dataset__id', 'test_dataset__name',
                  'train_dataset__name', 'data_type', 'send_email_on_change',
                  'state', 'net_type', 'traceback')


class TrainEnsembleManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return TrainEnsembleQuerySet(self.model)


class TrainEnsemble(models.Model):
    # states
    ST_NEW = 'NEW'
    ST_QUEUE = 'QUEUE'
    ST_TRAIN = 'TRAIN'
    ST_STOP = 'STOPPED'
    ST_ERROR = 'ERROR'
    ST_FINISH = 'FINISHED'
    ST_EMPTY = 'EMPTY'
    ST_DELETE = 'DELETED'
    STATES = (
        (ST_NEW, 'new'),
        (ST_QUEUE, 'in queue'),
        (ST_TRAIN, 'training'),
        (ST_STOP, 'stopped'),
        (ST_ERROR, 'error'),
        (ST_FINISH, 'finished'),
        (ST_EMPTY, 'empty'),
        (ST_DELETE, 'deleted'),
    )
    # nonlins
    SOFTMAX = 'SOFTMAX'
    SIGMOID = 'SIGMOID'
    SQ_SIGMOID = 'SQ_SIGMOID'
    LINEAR = 'LINEAR'
    LINEARGAUSSIAN = 'LINEARGAUSSIAN'
    OUT_NONLINS = (
        (SOFTMAX, 'softmax'),
        (SIGMOID, 'sigmoid'),
        (SQ_SIGMOID, 'sigmoid w/ MSE loss'),
        (LINEAR, 'linear w/ MSE loss'),
        (LINEARGAUSSIAN, 'linear gaussian')
    )
    # data types
    TIMESERIES = 'TIMESERIES'
    IMAGES = 'IMAGES'
    GENERAL = 'GENERAL'
    DATA_TYPES = (
        (TIMESERIES, 'Timeseries'),
        (IMAGES, 'Images'),
        (GENERAL, 'General ersatz format')
    )
    NET_DEEPNET = 'DEEPNET'
    NET_AUTOENCODER = 'AUTOENCODER'
    NET_RNN = 'RNN'
    NET_TSNE = 'TSNE'
    NET_TYPES = (
        (NET_DEEPNET, 'Deep Neural Network'),
        (NET_AUTOENCODER, 'Autoencoder Neural Network'),
        (NET_RNN, 'Recurent Neural Network'),
        (NET_TSNE, 'T-Distributed Stochastic Neighbor Embedding')
    )

    class Meta(object):
        ordering = ['-id']

    # fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='train_ensembles',
        verbose_name="user who created job"
    )
    created = models.DateTimeField('creation time', auto_now_add=True)
    train_dataset = models.ForeignKey(
        DataSet, verbose_name="data set for training", null=True,
        blank=True, related_name='ensembles_as_train'
    )
    test_dataset = models.ForeignKey(
        DataSet, verbose_name="data set for testing",
        null=True, blank=True, related_name='ensembles_as_test'
    )
    valid_dataset = models.ForeignKey(
        DataSet, verbose_name="data set for validating",
        null=True, blank=True, related_name='ensembles_as_valid'
    )
    queue_key = models.CharField(
        "key of last queue message with this ensemble",
        max_length=40, null=True
    )
    traceback = models.TextField('traceback from worker',
                                 null=True, blank=True)
    error = models.TextField('error from worker', null=True, blank=True)
    canceled = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    quantiles = JSONField("quantiles", null=True)
    config = JSONField("spearmint config", null=True)
    out_nonlin = models.CharField(
        'output nonlinearity', max_length=20, default=SOFTMAX, null=True,
        choices=OUT_NONLINS)
    data_type = models.CharField('data type', max_length=20,
                                 choices=DATA_TYPES, null=True)
    net_type = models.CharField('neural network type', max_length=20,
                                choices=NET_TYPES)
    options = JSONField("varios options", default=dict)
    shared = models.BooleanField(default=False)
    send_queue_time = models.DateTimeField('time of last sending to queue',
                                           null=True)
    send_email_on_change = models.BooleanField('send email on status change',
                                               default=False)
    state = models.CharField('ensemble state', max_length=15,
                             default=ST_EMPTY, choices=STATES)
    old_data = JSONField("old data ids", null=True)

    objects = TrainEnsembleManager()

    def save(self, *args, **kwargs):
        if not self.id or not TrainEnsemble.objects.get(pk=self.pk).shared:
            self.shared = False
            super(TrainEnsemble, self).save(*args, **kwargs)
        else:
            logger.warning('Saving not permitted on shared ensembles')
        self.clean_cache()

    def __unicode__(self):
        return "TrainEnsemble #%s" % self.pk

    def clean_cache(self):
        cache.delete('ensemble:%s:file_name' % self.pk)

    def get_queue_position(self):
        if self.state == self.ST_QUEUE and self.send_queue_time is not None:
            queue_after_me = TrainEnsemble.objects.on_worker() \
                .filter(learn_models__state='QUEUE',
                        send_queue_time__gt=self.send_queue_time) \
                .distinct().count()
            queue_size = get_queue_size()
            if queue_size is not None:
                position = queue_size - queue_after_me
                if position > 0:
                    return position
        return None

    @property
    def file_name(self):
        _file_name = cache.get('ensemble:%s:file_name' % self.pk)
        if _file_name:
            return _file_name
        if self.train_dataset:
            _file_name = self.train_dataset.key
        cache.set('ensemble:%s:file_name' % self.pk, _file_name)
        return _file_name

    def update_state(self):
        states = set(self.learn_models.live().values_list('state', flat=True))
        if not states:
            self.state = self.ST_EMPTY
        elif states == {'FINISHED'}:
            self.state = self.ST_FINISH
        elif states == {'NEW'}:
            self.state = self.ST_NEW
        elif states == {'NEW', 'FINISHED'}:
            self.state = self.ST_STOP
        elif states == {'CANCELED', 'FINISHED'}:
            self.state = self.ST_STOP
        else:
            return
        self.save()

    def get_deleted_models_time(self):
        time = self.learn_models.deleted().aggregate(time=Sum('training_time'))
        return time['time'] or 0.

    def get_deleted_predicts_time(self):
        times = PredictEnsemble.objects\
            .filter(iterations__model__ensemble=self)\
            .filter(iterations__discarded=True)\
            .distinct().values_list('predicting_time', flat=True)
        return sum(times)

    def to_delete_state(self):
        self.cancel_or_error()
        self.deleted = True
        self.state = self.ST_DELETE
        self.save()

    def is_datasets_valid(self):
        if self.data_type == 'GENERAL':
            try:
                lm = self.learn_models.live().values('model_name').latest('id')
                if lm['model_name'] == 'AUTOENCODER':
                    return self.train_dataset is not None
            except LearnModel.DoesNotExist:
                pass
        return self.train_dataset is not None and self.test_dataset is not None

    def _adjust_layer_params(self, message, model_params):
        """
        Ensures saving ensemble output out_nonlin and
        completes layer params based on ensemble output
        (irange or sparse_init).
        """
        try:
            message['out_nonlin'] = model_params['out_nonlin']
        except KeyError:
            message['out_nonlin'] = self.out_nonlin
        if self.out_nonlin != message['out_nonlin']:
            self.out_nonlin = message['out_nonlin']
            self.save()

        # WARNING! Temporary solution!
        # Find a cause of not feeding correct parameters to UI,
        # and fix it to get rid of the following!
        if message['name'] == 'MLP_MAXOUT_CONV':
            return message

        try:
            default_layer = get_default_settings(message['name'])['layers'][0]
        except (KeyError, IndexError):
            return message

        for layer in message['model_params']['layers']:
            for parm_name, parm_val in default_layer.iteritems():
                if parm_name not in layer:
                    layer.update({parm_name: parm_val})
            if self.out_nonlin == 'LINEARGAUSSIAN':
                del layer['sparse_init']
            else:
                del layer['irange']
        return message

    def send_to_queue(self, resume_model_stat=None, restart_model=None):
        #if auto_next_model then push to queue all models, else only requested
        key = sha1('%s:%s:%s' % (id(self), timezone.now(), 'Queue.Salt')) \
            .hexdigest()
        self.canceled = False
        self.error = None
        self.traceback = None
        self.state = self.ST_QUEUE
        self.queue_key = key
        self.send_queue_time = timezone.now()
        self.save()
        train_models = []
        sp_results = ''
        resume_model_id = None

        if resume_model_stat:
            resume_model_id = resume_model_stat.model_id
        elif restart_model:
            resume_model_id = restart_model.id
        learn_models = self.learn_models.live().order_by('pk')

        for model in learn_models:
            # if model finished use sp_results from it
            # unless job resume this model
            if model.state == 'FINISHED' and model.id != resume_model_id:
                if model.sp_results:
                    sp_results += model.sp_results + '\n'

        if resume_model_stat:
            message = resume_model_stat.get_model_training_message()
            message = self._adjust_layer_params(message, model.model_params)
            train_models.append(message)
        elif restart_model:
            message = restart_model.get_training_message()
            message = self._adjust_layer_params(message, model.model_params)
            train_models.append(message)
        else:
            for model in learn_models.exclude(state='FINISHED'):
                message = model.get_training_message()
                message = self._adjust_layer_params(message, model.model_params)
                train_models.append(message)
        message = {
            'ensemble': self.id,
            'sp_results': sp_results, 'queue_key': self.queue_key,
            'config': self.config, 'models': train_models,
            'quantiles': self.quantiles, 'data_type': self.data_type,
            'options': self.options
        }
        message['train_dataset'] = self.train_dataset.get_training_message()
        if self.test_dataset:
            message['test_dataset'] = self.test_dataset.get_training_message()
        else:
            message['test_dataset'] = None
        if self.valid_dataset:
            message['valid_dataset'] = \
                self.valid_dataset.get_training_message()
        else:
            message['valid_dataset'] = None
        meta = self.train_dataset.data.meta
        if self.data_type == 'TIMESERIES' and isinstance(meta, dict):
            try:
                if self.train_dataset.data.version > 2:
                    val = meta['max_timesteps']
                else:
                    val = meta['ts']['stats']['max_timesteps']
            except KeyError:
                pass
            else:
                message['options']['max_timesteps'] = val
        elif self.data_type == 'IMAGES':
            outputs = self.train_dataset.data.get_cifar_outputs_num()
            message['final_output'] = outputs
            #message['options']['layers_cfg'] = CONV_LAYERS_CFG % {'outputs': outputs}
            #message['options']['layer_params_cfg'] = CONV_LAYER_PARAMS_CFG
        if queue_job(message):  # should not delete if queue_job method failed
            if resume_model_stat:
                resume_model_stat.model.stats.live()\
                    .filter(iteration__gt=resume_model_stat.iteration)\
                    .update(discarded=True)
            return True
        # set error to ensemble
        return False

    def start(self):
        is_sended = self.send_to_queue()
        if is_sended:
            for model in self.learn_models.live():
                model.state = 'QUEUE'
                model.save()
            return True
        else:
            transaction.rollback()
            return False

    def resume(self):
        if not self.state in (self.ST_STOP, self.ST_ERROR, self.ST_NEW,
                              self.ST_FINISH, self.ST_QUEUE):
            return False
        if self.shared:
            return False
        # because QuerySet method update works directly with db, we
        # must exclude readonly models on this stage
        learn_models = self.learn_models.live().select_for_update() \
            .filter(state__in=(JOB_STATE.CANCEL, JOB_STATE.ERROR,
                               JOB_STATE.NEW), readonly=False).order_by('pk')
        if not learn_models:
            return False
        learn_models.update(state=JOB_STATE.QUEUE)
        is_sended = self.send_to_queue()
        if is_sended:
            return True
        else:
            transaction.rollback()
            return False

    def finished_models(self):
        return self.learn_models.filter(state=JOB_STATE.FINISH).order_by('id')

    def cancel_or_error(self):
        state, queue_key = self.state, self.queue_key
        learn_models = self.learn_models.live().select_for_update()\
            .exclude(state__in=(JOB_STATE.FINISH, JOB_STATE.ERROR))
        for model in learn_models:
            model.state = JOB_STATE.CANCEL
            model.save()
        if self.learn_models.filter(state=JOB_STATE.ERROR).exists():
            self.state = self.ST_ERROR
        elif learn_models:
            self.canceled = True
            self.state = self.ST_STOP
        self.save()
        if state in (self.ST_QUEUE, self.ST_TRAIN):
            queue_job('STOP', queue=queue_key, durable=False, delivery_mode=1)

    def update_status(self, traceback=None, error=None, quantiles=None):
        if traceback:
            self.traceback = traceback
        if error:
            self.error = error
            self.cancel_or_error()
            self.state = self.ST_ERROR
        if quantiles:
            self.quantiles = quantiles
        self.save()

    def pass_requirements_for_worker_processing(self):
        user = ApiUser.objects.get(pk=self.user_id)
        allow = user.seconds_paid > user.seconds_spent
        if not allow:
            self.cancel_or_error()
        return allow

    def share(self):
        self.clean_cache()
        if self.state != self.ST_FINISH:
            return False
        TrainEnsemble.objects.filter(pk=self.pk).update(shared=True)
        self.learn_models.all().update(readonly=True)
        LearnModelStat.objects.filter(model__ensemble_id=self.id)\
            .update(readonly=True)
        if self.train_dataset:
            self.train_dataset.share()
        if self.test_dataset:
            self.test_dataset.share()
        if self.valid_dataset:
            self.valid_dataset.share()
        return True

    def trigger_email_on_change(self, old_state):
        states = (self.ST_FINISH, self.ST_TRAIN, self.ST_ERROR, self.ST_STOP)
        if self.state in states and \
           old_state != self.state and self.send_email_on_change:
            domain = Site.objects.get_current().domain
            body = ('The status of the ensemble #%s has changed to '
                    '<strong>%s</strong>.<br> '
                    'See the details here: http://%s/train-ensemble/%s/'
                    % (self.id, self.state, domain, self.id))
            email = EmailMessage(
                subject='Ersatz. Ensemble status has changed.',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=(self.user.email,)
            )
            email.content_subtype = "html"
            email.send(fail_silently=True)

    def get_defaultparams(self, model_name):
        return get_default_settings(model_name)

    def get_datasets_for_predict(self, user):
        if self.train_dataset:
            return self.train_dataset\
                .datasets_with_same_structure(user, with_output=False)
        else:
            return []


class LearnModelQuerySet(QuerySet):
    def all_sorted(self):
        return self.order_by('pk')

    def live(self):
        return self.exclude(state=JOB_STATE.DELETE)

    def deleted(self):
        return self.filter(state=JOB_STATE.DELETE)

    def visible_to(self, user):
        return self.live().filter(Q(ensemble__user=user) |
                                  Q(ensemble__shared=True))


class LearnModelManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return LearnModelQuerySet(self.model)


class LearnModel(models.Model):
    MRNN = 'MRNN'
    CONV = 'CONV'
    AUTO = 'AUTOENCODER'
    SIGMOID = 'MLP_SIGMOID'
    RECTIFIED = 'MLP_RECTIFIED'
    MAXOUT = 'MLP_MAXOUT'
    MAXOUT_CONV = 'MLP_MAXOUT_CONV'
    TSNE = 'TSNE'
    TRAIN_MODELS = (
        (MRNN, 'MRNN'),
        (CONV, 'Convolutional Net'),
        (AUTO, 'Autoencoder'),
        (TSNE, 'T-SNE'),
        (SIGMOID, 'Deep Net Sigmoid'),
        (RECTIFIED, 'Deep Net Rectified'),
        (MAXOUT, 'Deep Net Maxout'),
        (MAXOUT_CONV, 'Deep Net Maxout Convolutional'),
    )
    GET_TRAIN_MODEL_NAME = dict(TRAIN_MODELS)
    MODEL_DATATYPE = {
        TrainEnsemble.TIMESERIES: [MRNN],
        TrainEnsemble.IMAGES: [CONV],
        TrainEnsemble.GENERAL: [AUTO, SIGMOID, RECTIFIED, MAXOUT, MAXOUT_CONV]
    }
    TRAIN_STATES = GENERAL_STATES + ((JOB_STATE.TRAIN, 'training'),
                                     (JOB_STATE.CANCEL, 'stopped'),
                                     (JOB_STATE.DELETE, 'deleted'))

    ensemble = models.ForeignKey(TrainEnsemble, related_name='learn_models',
                                 verbose_name="train ensemble")
    model_name = models.CharField("model name", max_length=255,
                                  choices=TRAIN_MODELS, default=MRNN)
    model_params = JSONField('model parameters', default={})
    created = models.DateTimeField('creation time', auto_now_add=True)
    updated = models.DateTimeField('time of last save', auto_now=True)
    state = models.CharField('job state', max_length=10,
                             choices=TRAIN_STATES, default=JOB_STATE.NEW)
    traceback = models.TextField('traceback from worker',
                                 null=True, blank=True)
    error = models.TextField('error from worker', null=True, blank=True)
    detailed_results_file = models.FileField(
        'detailed results file', upload_to='detailed_results', null=True
    )
    sp_results = models.TextField('spearmint results', null=True)
    training_time = models.FloatField(default=0.)
    readonly = models.BooleanField(default=False)
    name = models.CharField("name", max_length=255, null=True, blank=True)
    training_logs = models.TextField('training logs', null=True, blank=True)

    objects = LearnModelManager()

    def save(self, *args, **kwargs):
        if not self.id and not self.model_params:
            # case when user click add one more model
            self.model_params = \
                self.ensemble.get_defaultparams(self.model_name)
        if not self.id:
            if self.model_name == 'CONV':
                self.model_params['save_freq'] = 20
                self.model_params['test_freq'] = 10
            elif (self.model_name == 'AUTOENCODER' and
                  not self.model_params.get('save_freq')):
                self.model_params['save_freq'] = 25
            elif self.model_name.startswith('MLP_'):
                if not self.model_params.get('save_freq'):
                    self.model_params['save_freq'] = 25
                if 'learning_rate' in self.model_params:
                    constant = self.model_params['learning_rate'].get(
                        'constant', False
                    )
                    self.model_params['learning_rate']['constant'] = constant
                else:
                    self.model_params['learning_rate'] = {'constant': False}
                if 'momentum' in self.model_params:
                    constant = self.model_params['momentum'].get('constant',
                                                                 False)
                    self.model_params['momentum']['constant'] = constant
                else:
                    self.model_params['momentum'] = {'constant': False}

        if not self.id or not LearnModel.objects.get(pk=self.pk).readonly:
            super(LearnModel, self).save(*args, **kwargs)
            self.ensemble.update_state()
        else:
            logger.warning('Saving not permitted on read only models.')
        cache.delete('ensemble:%s:state' % self.ensemble_id)

    def __unicode__(self):
        return u'id:%s model:%s ensemble:%s file:%s' % (
            self.pk, self.model_name, self.ensemble, self.ensemble.file_name
        )

    def to_error_state(self, error, traceback):
        self.state = 'ERROR'
        self.error = error
        self.traceback = traceback
        self.save()
        self.ensemble.cancel_or_error()

    def to_finish_state(self, sp_results, detailed_results):
        self.sp_results = sp_results.strip()
        prefix = ''.join([random.choice(string.digits + string.letters)
                          for _ in range(0, 8)])
        self.detailed_results_file.save(prefix + '_' + str(self.pk) + '.txt',
                                        ContentFile(detailed_results))
        self.state = 'FINISHED'
        self.save()
        self.ensemble.update_state()

    def exract_hyperparams(self):
        """
        Extracts configuration for hyperparameters from config file,
        using OrderedDict, because order of element matters.
        """
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'hyperparams',
                               self.model_name.lower() + '.json'), 'r') as f:
            sp_config = json.loads(f.read(), object_pairs_hook=OrderedDict)
        return hp.HyperParams(sp_config.keys(), **sp_config)

    def unroll_params(self, params, unrolled, parent=None):
        """
        Recursively flattens nested dictionaries of arbitrary number of levels.
        """
        for key, val in params.iteritems():
            updated_key = '%s_%s' % (parent, key) if parent else key
            if isinstance(val, dict):
                self.unroll_params(val, unrolled, updated_key)
            else:
                unrolled[updated_key] = val
        return unrolled

    def user_finalize(self):
        """
        Finalizes model training, saves statistics gathered so far.
        """
        data = self.stats.live().best_test_accuracy_data()
        if self.model_params and self.training_time and data:
            hyperparams = self.exract_hyperparams()
            sp_results = [data.get('test_loss', 1),
                          int(max(self.training_time, 1))]
            unrolled = {}
            unrolled = self.unroll_params(self.model_params, unrolled)
            for name in hyperparams.names:
                try:
                    sp_results.append(unrolled[name])
                except KeyError:
                    pass
            self.sp_results = ' '.join(str(x) for x in sp_results)
            model_params = {}
            model_params['maxnum_iter'] = int(
                self.stats.live().order_by('-iteration')[0].data['iteration']
            )
            self.update_model_params_no_save(model_params)
            self.state = 'FINISHED'
            self.save()
            self.ensemble.update_state()
        else:
            return ("Model doesn't have enough data for finishing, "
                    "collect more statistics or delete it")

    def to_delete_state(self):
        self.state = 'DELETED'
        self.save()
        self.ensemble.update_state()

    def resume(self, iteration=None):
        '''resume model from iteration'''
        if self.state not in ('CANCELED', 'ERROR', 'FINISHED'):
            raise BadOperation()
        ensemble = self.ensemble
        if not ensemble.state in (ensemble.ST_STOP, ensemble.ST_ERROR,
                                  ensemble.ST_NEW, ensemble.ST_FINISH,
                                  ensemble.ST_QUEUE):
            raise BadOperation()
        if ensemble.shared:
            raise BadOperation()
        if iteration is None:
            restart_model = self
        else:
            restart_model = None
        is_sended = self.ensemble.send_to_queue(resume_model_stat=iteration,
                                                restart_model=restart_model)
        if not is_sended:
            raise BadOperation()
        self.state = 'QUEUE'
        self.save()

    def restart(self):
        self.stats.live().update(discarded=True)
        self.state = 'CANCELED'
        #delete s3_data from amazon
        return self.resume()

    def base_training_message(self):
        return {'id': self.id, 'name': self.model_name,
                'model_params': self.model_params}

    def get_training_message(self):
        message = self.base_training_message()
        try:
            data = self.stats.live().latest('iteration').s3_data
            message['resume'] = True
            message['resume_X'] = data
            data = self.stats.live().best_test_accuracy_data()
            message['high_score'] = data.get('test_accuracy')
            message['lower_loss'] = data.get('test_loss')
        except LearnModelStat.DoesNotExist:
            pass
        return message

    def create_stat(self, data, s3_data):
        LearnModelStat.objects.create(
            model=self,
            data=data,
            iteration=data['iteration'],
            test_accuracy=data['test_accuracy'],
            train_accuracy=data['train_accuracy'],
            s3_data=s3_data
        )

    def add_stat(self, data, s3_data):
        self.create_stat(data, s3_data)
        self.inc_training_time(data['time'])

    def inc_training_time(self, time):
        ApiUser.objects.filter(pk=self.ensemble.user_id)\
            .update(seconds_spent=F('seconds_spent') + time)
        LearnModel.objects.filter(pk=self.pk)\
            .update(training_time=F('training_time') + time)

    def update_status(self, state, error='', traceback='', sp_results=None,
                      detailed_results=None, model_params=None):
        self.ensemble.clean_cache()
        old_state = self.ensemble.state
        if state == 'ERROR':
            self.to_error_state(error, traceback)
        elif state == 'FINISHED':
            self.to_finish_state(sp_results, detailed_results)
        else:
            self.state = state
            if model_params:
                self.update_model_params_no_save(model_params)
            self.save()
            if self.state == "TRAIN":
                self.ensemble.state = self.ensemble.ST_TRAIN
            elif self.state == "QUEUE":
                self.ensemble.state = self.ensemble.ST_QUEUE
            self.ensemble.save()
        self.ensemble.trigger_email_on_change(old_state)

    def update_model_params_no_save(self, new):
        deep_update(self.model_params, new)

    def pass_requirements_for_worker_processing(self):
        user = ApiUser.objects.get(pk=self.ensemble.user_id)
        allow = user.seconds_paid > user.seconds_spent
        if not allow:
            self.ensemble.cancel_or_error()
        return allow

    def has_many_iters(self):
        return self.model_name in ('MRNN',)


class ConvModel(LearnModel):
    class Meta(object):
        proxy = True

    def add_stat(self, data, s3_data):
        try:
            stat = self.stats.live().latest('id')
            stat.data = data
            stat.iteration = data['iteration']
            stat.test_accuracy = data['test_accuracy']
            stat.train_accuracy = data['train_accuracy']
            stat.s3_data = s3_data
            stat.save()
        except LearnModelStat.DoesNotExist:
            self.create_stat(data, s3_data)
        self.inc_training_time(data['time'])

    def to_finish_state(self, sp_results, *args, **kwargs):
        self.sp_results = sp_results.strip()
        self.state = 'FINISHED'
        self.save()
        self.ensemble.update_state()


class AutoEncoderModel(ConvModel):

    class Meta(object):
        proxy = True


#import ipdb
class TSNEModel(ConvModel):

    class Meta(object):
        proxy = True

    def to_finish_state(self, sp_results, *args, **kwargs):
        #self.sp_results = sp_results.strip()
        #self.tsne_results = json.loads(args[0])
        self.state = 'FINISHED'
        self.save()
        self.ensemble.update_state()


class DeepNetModel(ConvModel):

    class Meta(object):
        proxy = True


class LearnModelStatQuerySet(QuerySet):
    def live(self):
        return self.exclude(discarded=True)

    def best_test_accuracy_data(self):
        try:
            return self.latest('test_accuracy').data
        except self.model.DoesNotExist:
            return {}


class LearnModelStatManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return LearnModelStatQuerySet(self.model)


class LearnModelStat(models.Model):
    model = models.ForeignKey(LearnModel, verbose_name="model",
                              related_name="stats")
    created = models.DateTimeField('creation time', auto_now_add=True)
    iteration = models.IntegerField('train iteration')
    test_accuracy = models.FloatField()
    train_accuracy = models.FloatField()
    data = JSONField("training stats")
    discarded = models.BooleanField(default=False)
    s3_data = models.CharField(max_length=255, verbose_name='S3 file path')
    readonly = models.BooleanField(default=False)

    objects = LearnModelStatManager()

    def save(self, *args, **kwargs):
        if not self.id or not LearnModelStat.objects.get(pk=self.pk).readonly:
            super(LearnModelStat, self).save(*args, **kwargs)
        else:
            logger.warning('Saving not permitted on read only stats.')

    def get_model_training_message(self):
        message = self.model.base_training_message()
        message['resume'] = True
        message['resume_X'] = self.s3_data
        data = self.model.stats.live().filter(iteration__lte=self.iteration)\
            .best_test_accuracy_data()
        message['high_score'] = data.get('test_accuracy')
        message['lower_loss'] = data.get('test_loss')
        return message

    @classmethod
    def select_model_iteration(cls, model_iter):
        query = Q()
        for entry in model_iter:
            query |= Q(iteration=entry['iteration'],
                       model=entry['id'], discarded=False)
        return cls.objects.filter(query)


class PredictEnsembleQuerySet(QuerySet):
    def on_worker(self):
        return self.exclude(state__in=('ERROR', 'FINISHED'))\
            .order_by('-pk').prefetch_related('iterations')

    def finished(self):
        return self.exclude(state__in=('NEW', 'QUEUE', 'PREDICT', 'ERROR'))\
            .order_by('-pk').prefetch_related('iterations')

    def canceled(self):
        return self.filter(state='ERROR')\
            .order_by('-pk').prefetch_related('iterations')

    def visible_to(self, user):
        return self.live().filter(user=user)

    def live(self):
        return self.exclude(iterations__discarded=True)


class PredictEnsembleManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return PredictEnsembleQuerySet(self.model)


class PredictEnsemble(models.Model):
    PREDICT_STATES = GENERAL_STATES + ((JOB_STATE.PREDICT, 'predict'),)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             related_name='predict_ensembles',
                             verbose_name="user who created job")
    input_data = models.TextField("input data for predict",
                                  null=True, blank=True)
    created = models.DateTimeField('creation time', auto_now_add=True)
    iterations = models.ManyToManyField(LearnModelStat, through='Predict')
    traceback = models.TextField('traceback from worker',
                                 null=True, blank=True)
    error = models.TextField('error from worker', null=True, blank=True)
    results = JSONField("predict results", null=True)
    queue_key = models.CharField(
        "key of last queue message with this ensemble",
        max_length=40, null=True
    )
    dataset = models.ForeignKey(DataSet, verbose_name="dataset for predict",
                                null=True, blank=True)
    state = models.CharField('job state', max_length=10,
                             choices=PREDICT_STATES, default=JOB_STATE.NEW)
    predicting_time = models.FloatField(default=0.)
    s3key = models.CharField('s3 key for images',
                             null=True, blank=True, max_length=250)

    objects = PredictEnsembleManager()

    def push_predicts_to_queue(self):
        if self.send_to_queue():
            self.state = 'QUEUE'
            self.save()
            return True
        else:
            # rollback predict ensemble and all predicts
            transaction.rollback()
            return False

    def create_predicts(self, iterations):
        for iteration in iterations:
            Predict.objects.create(iteration=iteration, ensemble=self)
        return self.push_predicts_to_queue()

    def inc_predicting_time(self, time):
        ApiUser.objects.filter(pk=self.user_id)\
            .update(seconds_spent=F('seconds_spent') + time)
        PredictEnsemble.objects.filter(pk=self.pk)\
            .update(predicting_time=F('predicting_time') + time)

    def send_to_queue(self):
        key = sha1('%s:%s:%s' % (id(self), timezone.now(), 'Queue.Salt'))
        self.queue_key = key.hexdigest()
        self.save()
        predicts = self.predicts.all().values(
            'id',
            'iteration_id',
            'iteration__model__ensemble__out_nonlin',
            'iteration__model__model_name',
            'iteration__s3_data',
            'iteration__model__id',
            'iteration__model__model_params'
        )
        if not predicts:
            return False
        predicts = [
            {
                'id': p['id'],
                'iteration_id': p['iteration_id'],
                'out_nonlin': p['iteration__model__ensemble__out_nonlin'],
                'model_name': p['iteration__model__model_name'],
                'model_id': p['iteration__model__id'],
                's3_data': p['iteration__s3_data'],
                'model_params': json.loads(p['iteration__model__model_params'])
            } for p in predicts]
        ensemble = self.predicts.get(id=predicts[0]['id'])\
            .iteration.model.ensemble
        message = {
            'ensemble': self.id,
            'queue_key': self.queue_key,
            'predicts': predicts,
            'quantiles': ensemble.quantiles,
            'data_type': ensemble.data_type,
            'train_ensemble_id': ensemble.id,
            'options': ensemble.options
        }
        train_dataset_msg = ensemble.train_dataset.get_training_message()
        if self.dataset:
            dataset_msg = self.dataset.get_training_message()
            # Always use dtypes and classes from training dataset!
            dataset_msg['data']['dtypes'] = train_dataset_msg['data']['dtypes']
            dataset_msg['data']['classes'] = train_dataset_msg['data']['classes']
            message.update({
                'dataset': dataset_msg,
                'MODE': 'DATASET',
                'INPUT_ONLY': self.dataset.data.is_ts_and_input_only()
            })
        else:
            message['dataset'] = train_dataset_msg
            message['input_data'] = self.input_data
            if ensemble.data_type == 'IMAGES':
                message['input_data'] = self.s3key
        return queue_job(message, 'predict')

    def update_status(self, time, traceback=None, error=None, results=None):
        if traceback or error:
            self.traceback = traceback
            self.error = error
            self.state = 'ERROR'
        if results:
            self.results = results
            self.state = 'FINISHED'
        self.save()
        self.inc_predicting_time(time)


class Predict(models.Model):
    ensemble = models.ForeignKey(PredictEnsemble, related_name='predicts')
    iteration = models.ForeignKey(LearnModelStat, related_name='predicts')

LEARN_MODELS = {'MRNN': LearnModel,
                'CONV': ConvModel,
                'TSNE': TSNEModel,
                'AUTOENCODER': AutoEncoderModel,
                'MLP_SIGMOID': DeepNetModel,
                'MLP_RECTIFIED': DeepNetModel,
                'MLP_MAXOUT': DeepNetModel,
                'MLP_MAXOUT_CONV': DeepNetModel}
