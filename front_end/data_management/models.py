import os
import json
from contextlib import contextmanager
from dateutil.parser import parse as dt_parse
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.utils.datetime_safe import datetime
from django.utils.timezone import utc
from django.conf import settings
from django.db.models.query import QuerySet
from celery import Celery
from jsonfield import JSONField
from core.models import CustomManager
from core.utils import redis_publish, build_url, build_key


class DataFileQuerySet(QuerySet):
    def not_deleted(self):
        return self.exclude(state__in=[4, 5])

    def supported_training(self):
        return self.not_deleted().exclude(file_format__isnull=True) \
            .exclude(file_format='UNSUPPORTED')

    def visible_to(self, user):
        return self.not_deleted().filter(Q(user=user) | Q(shared=True))

    def for_serialization(self):
        return self.prefetch_related('parse_logs', 'datasets')\
            .only('id', 'name', 'created', 'state',
                  'file_format', 'meta', 'shared')


class DataFileManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return DataFileQuerySet(self.model)


class DataFile(models.Model):

    class Meta(object):
        ordering = ['-last_touch']

    STATES = (STATE_UPLOADING, STATE_UPLOADED, STATE_PARSING_META,
              STATE_READY, STATE_DELETING, STATE_DELETED,
              STATE_UPLOAD_FAILED, STATE_PARSE_FAILED,
              STATE_CONVERSION_FAILED, STATE_CONVERTING,
              STATE_ACTION_REQUIRED) = range(11)
    STATES_CHOICES = [
        (STATE_UPLOADING, 'Uploading'),
        (STATE_UPLOADED, 'Uploaded'),
        (STATE_PARSING_META, 'Parsing'),
        (STATE_READY, 'Ready'),
        (STATE_DELETING, 'Deleting'),
        (STATE_DELETED, 'Deleted'),
        (STATE_UPLOAD_FAILED, 'Upload Failed'),
        (STATE_PARSE_FAILED, 'Parse Failed'),
        (STATE_CONVERSION_FAILED, 'Conversion Failed'),
        (STATE_CONVERTING, 'Converting'),
        (STATE_ACTION_REQUIRED, 'Action required'),
    ]
    TIMESERIES = 'TIMESERIES'
    IMAGES = 'IMAGES'
    GENERAL = 'GENERAL'
    UNSUPPORTED = 'UNSUPPORTED'
    FORMATS_CHOICES = (
        (TIMESERIES, 'Timeseries'),
        (IMAGES, 'Images'),
        (GENERAL, 'General'),
        (UNSUPPORTED, 'Unsupported'),
    )

    state = models.IntegerField(choices=STATES_CHOICES,
                                default=STATE_UPLOADING)
    created = models.DateTimeField('creation time', auto_now_add=True)
    last_touch = models.DateTimeField(auto_now_add=True, auto_now=True,
                                      null=True, blank=True)
    key = models.CharField(max_length=255, unique=True, blank=True)
    bucket = models.CharField(max_length=255, blank=True,
                              default=settings.S3_BUCKET)
    meta = JSONField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='s3files')
    celery_task_id = models.CharField(max_length=100, blank=True)
    file_format = models.CharField(max_length=20,
                                   choices=FORMATS_CHOICES, null=True)
    name = models.CharField(max_length=255, blank=True)
    shared = models.BooleanField(default=False)
    version = models.IntegerField(default=settings.DMWORKER_VERSION)
    local_file = models.FileField(
        'temporary local data file',
        upload_to=lambda s, n: build_key(s.user.id, n, 'datafiles'),
        null=True
    )

    objects = DataFileManager()

    def __unicode__(self):
        return self.filename + u':' + unicode(self.id)

    @property
    def filename(self):
        return self.name or os.path.split(self.key)[-1]

    def touch(self):
        self.last_touch = datetime.now()

    def need_reparse(self):
        return self.meta is not None and self.meta.get('version', 2) < 3

    def schedule_parsing(self):
        url = build_url(reverse('dm_parsed', kwargs={'datafile_id': self.id}))
        api_file = None
        if self.local_file.name:
            api_file = build_url(self.local_file.url)
        with Celery(set_as_current=False) as app:
            app.config_from_object(settings.DMWORKER_CELERY_CONFIG)
            task = app.send_task('dmworker.tasks.parse',
                                 args=(self.key, url, api_file),
                                 countdown=1)
        self.parse_logs.all().delete()
        self.parsing_log_add(datetime.now(), 'Waiting in queue...')
        self.state = DataFile.STATE_PARSING_META
        self.celery_task_id = task.id

        self.touch()
        self.save()

    def schedule_delete(self):
        url = build_url(reverse('dm_deleted',
                                kwargs={'datafile_id': self.id}))
        with Celery(set_as_current=False) as app:
            app.config_from_object(settings.DMWORKER_CELERY_CONFIG)
            task = app.send_task('dmworker.tasks.delete',
                                 args=(self.key, url))
        self.celery_task_id = task.id
        self.state = DataFile.STATE_DELETING

        self.touch()
        self.save()

    def on_swap_to_zip(self):
        with Celery(set_as_current=False) as app:
            app.config_from_object(settings.DMWORKER_CELERY_CONFIG)
            app.send_task('dmworker.tasks.delete_not_compressed',
                          args=(self.key,))

    @contextmanager
    def get_celery_result(self):
        with Celery(set_as_current=False) as app:
            app.config_from_object(settings.DMWORKER_CELERY_CONFIG)
            yield app.AsyncResult(self.celery_task_id)

    def check_parsing_status(self):
        with self.get_celery_result() as result:
            if result.status == 'FAILURE':
                self.state = DataFile.STATE_PARSE_FAILED
                self.save()
                self.publish_state()

    @property
    def is_ready(self):
        return self.state == DataFile.STATE_READY

    @property
    def is_deleted(self):
        return self.state in (DataFile.STATE_DELETED, DataFile.STATE_DELETING)

    def get_max_timesteps(self):
        if self.meta and self.file_format == self.TIMESERIES:
            try:
                if self.version > 2:
                    return self.meta['max_timesteps']
                return self.meta['ts']['stats']['max_timesteps']
            except KeyError:
                pass
        return None

    def on_parsed(self, meta):
        if self.state == DataFile.STATE_PARSING_META:
            if meta['key'] != self.key:
                self.on_swap_to_zip()
                self.key = meta['key']
            self.meta = meta
            self.state = DataFile.STATE_READY
            self.file_format = self.meta['data_type']
            self.version = self.meta['version']
            if self.local_file.name:
                self.local_file.delete(save=False)
            self.touch()
            self.save()
            self.publish_state()

    def publish_state(self):
        redis_publish('dashboard_ws_%s' % self.user.pk,
                      json.dumps({
                          'type': 'data_file_update',
                          'data': self.get_state_message()
                      }))

    def on_deleted(self):
        if self.state == DataFile.STATE_DELETING:
            self.state = DataFile.STATE_DELETED
        self.touch()
        self.save()

    def get_cifar_outputs_num(self):
        if self.version > 2:
            return len(self.meta['classes'])
        return self.meta['num_classes']

    def support_training(self):
        # TODO: delete it?
        return (not self.file_format is None and
                self.file_format != 'UNSUPPORTED')

    def share(self):
        DataFile.objects.filter(pk=self.pk).update(shared=True)

    def parsing_log_add(self, timestamp, msg):
        if isinstance(timestamp, (str, unicode)):
            timestamp = dt_parse(timestamp).replace(tzinfo=utc)
        ParseLog.objects.create(timestamp=timestamp,
                                message=msg,
                                data_file=self)

    def get_state_message(self):
        return {
            'id': self.id,
            'name': self.name,
            'meta': self.meta,
            'created': self.created.isoformat(),
            'state': self.get_state_display(),
            'file_format': self.file_format,
            'shared': self.shared
        }

    def is_ts_and_input_only(self):
        return (self.file_format == 'TIMESERIES' and
                self.meta.get('output_size') == 0)


class DataSetQuerySet(QuerySet):
    def not_deleted(self):
        return self.exclude(state=DataSet.ST_DELETE)

    def visible_to(self, user):
        return self.not_deleted().filter(Q(user=user) | Q(shared=True))

    def for_serialization(self):
        return self.only('id', 'created', 'filters', 'shared', 'name')


class DataSetManager(CustomManager):
    use_for_related_fields = True

    def get_query_set(self):
        return DataSetQuerySet(self.model)


class DataSet(models.Model):

    ST_READY = 'READY'
    ST_DELETE = 'DELETED'
    STATES = (
        (ST_READY, 'Ready'),
        (ST_DELETE, 'Deleted'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='datasets')
    created = models.DateTimeField('creation time', auto_now_add=True)
    data = models.ForeignKey(DataFile, related_name='datasets')
    key = models.CharField(max_length=255, unique=True)
    filters = JSONField(default=list, blank=True)
    iscreated = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    state = models.CharField(max_length=15, choices=STATES, default=ST_READY)
    name = models.CharField(max_length=255)
    quantiles = JSONField(blank=True, null=True)
    norm_min_max = JSONField(blank=True, null=True)
    last_column_is_output = models.NullBooleanField(null=True)
    version = models.IntegerField(default=settings.DATASET_VERSION)

    objects = DataSetManager()

    def share(self):
        DataSet.objects.filter(pk=self.pk).update(shared=True)
        self.data.share()

    def eq_format(self, cmeta, clast_column_is_output, with_output=True):
        good_states = (DataFile.STATE_READY,
                       DataFile.STATE_DELETED,
                       DataFile.STATE_DELETING)
        #TODO: add tests
        if self.data.state not in good_states or not self.data.meta:
            return False
        meta = self.data.meta
        try:
            if self.data.file_format == 'TIMESERIES':
                if with_output:
                    return (meta['binary_input'] == cmeta['binary_input'] and
                            meta['binary_output'] == cmeta['binary_output'] and
                            meta['input_size'] == cmeta['input_size'] and
                            meta['output_size'] == cmeta['output_size'])
                else:
                    return (meta['binary_input'] == cmeta['binary_input'] and
                            meta['input_size'] == cmeta['input_size'])
            elif self.data.file_format == 'GENERAL':
                num_inputs = meta['num_columns']
                cnum_inputs = cmeta['num_columns']
                if self.last_column_is_output:
                    num_inputs -= 1
                    num_outputs = 1
                else:
                    num_outputs = 0
                if clast_column_is_output:
                    cnum_inputs -= 1
                    cnum_outputs = 1
                else:
                    cnum_outputs = 0

                if with_output:
                    return (num_inputs == cnum_inputs and
                            num_outputs == cnum_outputs)
                else:
                    return num_inputs == cnum_inputs
            else:
                return True
        except KeyError:
            return False

    def get_training_message(self):
        filters = []
        for flt in self.filters:
            if flt['name'] == 'merge':
                flt = flt.copy()
                dfs = DataFile.objects.filter(id__in=flt['datas'])\
                    .values_list('key', flat=True)
                flt['datas'] = list(dfs)
            filters.append(flt)
        data = {
            'id': self.data.id,
            'key': self.data.key,
            'data_type': self.data.file_format,
            }
        try:
            data.update({
                'min': self.data.meta.get('min', []),
                'max': self.data.meta.get('max', []),
                'mean': self.data.meta.get('mean', []),
                'stdev': self.data.meta.get('stdev', []),
                'dtypes': self.data.meta.get('dtypes', []),
                'classes': self.data.meta.get('classes', []),
                'delimiter': self.data.meta.get('delimeter', r'\s+'),
                'with_header': self.data.meta.get('with_header', False),
                'num_columns': self.data.meta.get('num_columns', 0)
                })
        except:
            pass
        return {
            'id': self.id,
            'key': self.key,
            'iscreated': self.iscreated,
            'filters': filters,
            'data': data,
            'quantiles': self.quantiles,
            'norm_min_max': self.norm_min_max,
            'last_column_is_output': self.last_column_is_output,
            'version': self.version,
        }

    def datasets_with_same_structure(self, user, with_output=True):
        qs = DataSet.objects.visible_to(user)\
            .filter(state=self.ST_READY,
                    data__file_format=self.data.file_format)\
            .select_related('data')\
            .only('id', 'name', 'data__meta', 'last_column_is_output')
        return [dset for dset in qs
                if self.eq_format(dset.data.meta,
                                  dset.last_column_is_output, with_output)]

    def is_visible_to(self, user):
        return (self.state != self.ST_DELETE and
                (self.user_id == user.id or self.shared))

    @property
    def deletable(self):
        return not self.ensembles_as_train.model.objects.live().filter(
            Q(train_dataset=self) |
            Q(test_dataset=self) |
            Q(valid_dataset=self)
        ).exists()


class ParseLog(models.Model):

    class Meta(object):
        ordering = ['timestamp']

    timestamp = models.DateTimeField('timestamp')
    message = models.TextField('message')
    data_file = models.ForeignKey(DataFile, related_name='parse_logs')

    def save(self, *args, **kwargs):
        is_new = self.id is None
        super(ParseLog, self).save(*args, **kwargs)
        if is_new:
            redis_publish('dashboard_ws_%s' % self.data_file.user_id,
                          json.dumps({
                              'type': 'parse_log',
                              'df_id': self.data_file_id,
                              'data': self.get_state_message()
                          }))

    def get_state_message(self):
        return {
            'id': self.pk,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message
        }
