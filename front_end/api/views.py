#coding: utf-8
import json
import logging
from functools import wraps
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from api.forms import (LearnModelStatForm, LearnModelStatusForm,
                       TrainEnsembleStatusForm, PredictEnsembleStatusForm,
                       ConvnetFileUploadForm)
from job.models import (LearnModel, LearnModelStat, TrainEnsemble,
                        PredictEnsemble, Predict)
from job.model_settings import get_default_settings
from data_management.models import DataFile, DataSet
from core.utils import build_key, upload_data_to_s3

from rest_framework import status
from rest_framework import mixins
from rest_framework import filters
from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.decorators import action, link
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from api.serializers import (DataFileSerializer, TrainEnsembleSerializer,
                             DataSetSerializer, LearnModelSerializer,
                             PredictEnsembleSerializer,
                             DataFileCreateSerializer)
from api.auth import UseKeyAuthentication
from api.permissions import HasPaidTime, IsSuperUser
from api.exceptions import (APIPermissionDenied,
                            APIBadRequest, APIStandardError)
from api.filters import (EnsembleFilterBackend, DataSetFilterBackend,
                         PredictFilterBackend)
from api.validators import (predict_ensemble_iterations_validator,
                            predict_ensemble_data_validator)
from job.exceptions import BadOperation


logger = logging.getLogger('api.views')


class AuthPermMixin(object):
    """
    Mixin with general authentication and permissions
    """

    authentication_classes = (UseKeyAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, HasPaidTime)


class EnsembleViewSet(AuthPermMixin, viewsets.ModelViewSet):
    serializer_class = TrainEnsembleSerializer
    filter_backends = (EnsembleFilterBackend, )
    model = TrainEnsemble

    def get_queryset(self):
        return TrainEnsemble.objects.visible_to(self.request.user)\
            .for_serialization()

    def pre_save(self, obj):
        obj.user = self.request.user
        if obj.train_dataset:
            obj.data_type = obj.train_dataset.data.file_format
        if obj.data_type == obj.TIMESERIES:
            obj.net_type = obj.NET_RNN
        elif obj.data_type == obj.IMAGES:
            obj.net_type = obj.NET_DEEPNET
        elif obj.data_type == obj.GENERAL:
            #if obj.test_dataset is None: #god damn it
                ##TODO Figure out how to distinguish between TSNE and AUTOENCODER
                ## given the information available to self and obj
                #obj.net_type = obj.NET_AUTOENCODER
            if self.request._data['net_type'] == 'AUTOENCODER':
                obj.net_type = obj.NET_AUTOENCODER
            elif self.request._data['net_type'] == 'TSNE':
                obj.net_type = obj.NET_TSNE
            else:
                obj.net_type = obj.NET_DEEPNET
        else:
            logger.critical('%s: unknown data_type', self.obj)

    def get_object(self):
        obj = super(EnsembleViewSet, self).get_object()
        if self.request.method.lower() != 'get' and obj.shared:
            raise APIPermissionDenied()
        return obj

    def destroy(self, request, pk):
        obj = self.get_object()
        obj.to_delete_state()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action()
    def stop(self, request, pk):
        obj = self.get_object()
        obj.cancel_or_error()
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action()
    def resume(self, request, pk):
        obj = self.get_object()
        if obj.state not in (obj.ST_ERROR, obj.ST_STOP, obj.ST_NEW):
            raise APIBadRequest('You should stop ensemble before restart.')
        if not obj.is_datasets_valid():
            raise APIBadRequest('Ensemble datasets are not configured.')
        is_sended_to_queue = obj.resume()
        if is_sended_to_queue:
            serializer = self.get_serializer(instance=obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise APIStandardError('Training service is unavailable, '
                                   'please try later.')

    @action(permission_classes=[IsAuthenticated, IsSuperUser])
    def share(self, request, pk):
        obj = self.get_object()
        success = obj.share()
        if not success:
            raise APIBadRequest("This ensemble can't be shared.")
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DataViewSet(AuthPermMixin, viewsets.ModelViewSet):
    """
    List, retrieve, update or delete a data instance.
    """
    serializer_class = DataFileSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('file_format', 'shared')
    ordering = ('-created', )
    model = DataFile

    def create(self, request, *args, **kwargs):
        self.is_create_request = True
        serializer = self.get_serializer(data=request.DATA,
                                         files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            serializer = DataFileSerializer(
                instance=self.object, context=self.get_serializer_context()
            )
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if getattr(self, 'is_create_request', False):
            return DataFileCreateSerializer
        return DataFileSerializer

    def get_queryset(self):
        return DataFile.objects.visible_to(self.request.user)\
            .for_serialization()

    def pre_save(self, obj):
        obj.user = self.request.user

    def post_save(self, obj, created=False):
        if created:
            obj.schedule_parsing()

    def get_object(self):
        obj = super(DataViewSet, self).get_object()
        if self.request.method.lower() != 'get' and obj.shared:
            raise APIPermissionDenied()
        return obj

    def destroy(self, request, pk):
        obj = self.get_object()
        obj.schedule_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action()
    def parse(self, request, pk):
        obj = self.get_object()
        if obj.need_reparse():
            obj.schedule_parsing()
            serializer = self.get_serializer(instance=obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise APIBadRequest('Parse not allowed.')

    @action(permission_classes=[IsAuthenticated, IsSuperUser])
    def share(self, request, pk):
        obj = self.get_object()
        obj.share()
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DataSetViewSet(AuthPermMixin,
                     mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """
    List, create, retrieve and delete a dataset instance
    """
    serializer_class = DataSetSerializer
    filter_backends = (DataSetFilterBackend, filters.OrderingFilter)
    filter_fields = ('data', )
    ordering = ('-created', )

    def get_queryset(self):
        return DataSet.objects.visible_to(self.request.user)\
            .for_serialization()

    def get_object(self):
        obj = super(DataSetViewSet, self).get_object()
        if self.request.method.lower() != 'get' and obj.shared:
            raise APIPermissionDenied()
        return obj

    def pre_save(self, objects):
        if not isinstance(objects, list):
            objects = [objects]
        for obj in objects:
            obj.user = self.request.user
            obj.key = build_key(self.request.user.id, obj.name,
                                prefix="uploads/dataset") + '.hdf5'

    def get_serializer(self, instance=None, data=None,
                       files=None, many=False, partial=False):
        if isinstance(data, list):
            many = True
        return super(DataSetViewSet, self).get_serializer(instance, data,
                                                          files, many, partial)

    def destroy(self, request, pk):
        obj = self.get_object()
        if obj.deletable:
            obj.state = obj.ST_DELETE
            obj.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise APIBadRequest("This dataset has ensembles, delete not allowed.")


class LearnModelViewSet(AuthPermMixin, viewsets.ModelViewSet):
    """
    Create, list models.
    """
    serializer_class = LearnModelSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('ensemble', )

    def get_queryset(self, queryset=None):
        return LearnModel.objects.visible_to(self.request.user)

    def get_serializer(self, instance=None, data=None,
                       files=None, many=False, partial=False):
        if isinstance(data, list):
            many = True
        return super(LearnModelViewSet, self).get_serializer(instance, data,
                                                             files, many,
                                                             partial)

    def pre_save(self, objects):
        if not isinstance(objects, list):
            objects = [objects]
        for obj in objects:
            if obj.model_name == 'MRNN':
                #FIXME: this only works if ensemble new
                ens = obj.ensemble
                ens.config = get_default_settings("SPEARMINT")
                ens.save()

    def get_object(self):
        obj = super(LearnModelViewSet, self).get_object()
        if self.request.method.lower() != 'get' and obj.readonly:
            raise APIPermissionDenied()
        return obj

    def destroy(self, request, pk):
        obj = self.get_object()
        if obj.state in ('TRAIN', 'QUEUE'):
            raise APIBadRequest({
                'status': 'fail',
                'problem': 'Model in state: %s. Can\'t be deleted' % obj.state
            })
        obj.to_delete_state()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action()
    def resume(self, request, pk):
        #TODO: more tests
        model = self._get_object_for_resume()
        if 'iteration' in request.DATA:
            try:
                iteration = model.stats.live()\
                    .get(iteration=request.DATA.get('iteration'))
            except (LearnModelStat.DoesNotExist, ValueError):
                raise APIBadRequest({'status': 'fail',
                                     'problem': 'Invalid iteration.'})
        else:
            try:
                iteration = model.stats.live().latest('iteration')
            except LearnModelStat.DoesNotExist:
                raise APIBadRequest({'status': 'fail',
                                     'problem': 'No iterations for resume.'})
        try:
            model.resume(iteration)
        except BadOperation:
            transaction.rollback()
            raise APIBadRequest({'status': 'fail',
                                 'problem': "Can't resume this model"})
        serializer = self.get_serializer(instance=model)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action()
    def restart(self, request, pk):
        model = self._get_object_for_resume(restart=True)
        try:
            model.restart()
        except BadOperation:
            transaction.rollback()
            raise APIBadRequest({'status': 'fail',
                                 'problem': "Can't restart this model"})
        serializer = self.get_serializer(instance=model)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action()
    def finalize(self, request, pk):
        #TODO: tests
        model = self.get_object()
        if model.state != 'CANCELED':
            raise APIBadRequest({'status': 'fail', 'problem': 'Bad request.'})
        error = model.user_finalize()
        if error:
            raise APIBadRequest({'status': 'fail', 'problem': error})
        serializer = self.get_serializer(instance=model)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_object_for_resume(self, restart=False):
        model = self.get_object()
        #TODO: readonly
        states = ('CANCELED', 'ERROR', 'FINISHED')
        if restart:
            states += ('NEW',)
        if model.state not in states:
            raise APIBadRequest({'status': 'fail',
                                 'problem': 'Model not in right state.'})
        return model

    @link()
    def stats(self, request, pk):
        obj = self.get_object()
        res = []
        stat_id__gt = 0
        if obj.has_many_iters():
            stat_id__gt = request.QUERY_PARAMS.get('stat_id__gt', 0)
        for stat_pk, data in obj.stats.live() \
                .filter(id__gt=stat_id__gt).order_by('iteration') \
                .values_list('pk', 'data'):
            data = json.loads(data, parse_constant=lambda x: 0.00001)
            data['id'] = stat_pk
            res.append(data)
        return HttpResponse(json.dumps(res), content_type='application/json')


class PredictViewSet(AuthPermMixin,
                     mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = PredictEnsembleSerializer
    filter_backends = (PredictFilterBackend, )
    model = PredictEnsemble

    def get_queryset(self):
        return PredictEnsemble.objects.visible_to(self.request.user)

    def pre_save(self, obj):
        obj.user = self.request.user
        try:
            self._predict_ensemble_iterations = \
                predict_ensemble_iterations_validator(
                    self.request.DATA.get('iterations'),
                    self.request.user
                )
        except serializers.ValidationError as exc:
            raise APIBadRequest(exc.message_dict)
        try:
            with_files = predict_ensemble_data_validator(
                self._predict_ensemble_iterations,
                obj.input_data,
                obj.dataset,
                self.request.FILES)
        except serializers.ValidationError as exc:
            try:
                raise APIBadRequest(exc.message_dict)
            except AttributeError:
                raise APIBadRequest(exc.messages)
        if with_files:
            files = []
            for k, v in self.request.FILES.iteritems():
                if not k.startswith('file-'):
                    continue
                form = ConvnetFileUploadForm({}, {'file': v})
                if not form.is_valid():
                    raise APIBadRequest({k: "Bad image file."})
                img = form.cleaned_data['file']
                img.name = k + '--' + img.name
                files.append(img)
            if not files:
                raise APIBadRequest("No images found.")
            from core.cifar import build_batch
            model = LearnModelStat.objects \
                .get(pk=self._predict_ensemble_iterations[0]).model
            file_ = build_batch(files, img_size=model.model_params['img_size'])
            key = build_key(self.request.user.pk, 'batch.pkl')
            upload_data_to_s3(key, file_)
            obj.s3key = key

    def post_save(self, obj, created=False):
        for iteration in self._predict_ensemble_iterations:
            Predict.objects.create(iteration_id=iteration, ensemble=obj)
        obj.push_predicts_to_queue()


def worker_api(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
            except ValueError:
                return HttpResponseForbidden(json.dumps({
                    'status': 'fail', 'problem': 'invalid json'
                }), content_type="application/json")
        else:
            data = request.GET
        if data.get('worker_key') != settings.WORKER_KEY:
            return HttpResponseForbidden(json.dumps({
                'status': 'fail', 'problem': 'invalid worker key'
            }), content_type="application/json")
        return f(request, data, *args, **kwds)
    return wrapper


#TODO: quick view for worker, replace with REST
@csrf_exempt
@require_POST
@worker_api
def dataset_patch(request, data):
    dataset = get_object_or_404(DataSet, pk=data.pop('id'))
    for k, v in data.items():
        setattr(dataset, k, v)
    dataset.save()
    return HttpResponse(json.dumps({'status': 'success'}),
                        content_type="application/json")


@csrf_exempt
@require_POST
@worker_api
def stats_view(request, data):
    form = LearnModelStatForm(data)
    if form.is_valid():
        cdata = form.cleaned_data
        model = cdata['model']
        model.add_stat(data=cdata['data'], s3_data=cdata['s3_data'])
        if not model.pass_requirements_for_worker_processing():
            return HttpResponseForbidden(
                json.dumps({'status': 'fail', 'problem': 'User out of time'}),
                content_type="application/json")
        return HttpResponse(json.dumps({'status': 'success'}),
                            content_type="application/json")
    return HttpResponseBadRequest(
        json.dumps({'status': 'fail', 'problem': form.errors}),
        content_type="application/json")


@csrf_exempt
@require_POST
@worker_api
def logs_view(request, data):
    try:
        model = LearnModel.objects.get(pk=data.get('model', 0))
        if data.get('is_new', False):
            model.training_logs = data.get('data', '')
        else:
            model.training_logs += data.get('data', '')
        model.save()
    except LearnModel.DoesNotExist:
        return None
    return HttpResponse(json.dumps({'status': 'success'}),
                        content_type="application/json")


@csrf_exempt
@require_POST
@worker_api
def worker_job_state_view(request, data):
    form = LearnModelStatusForm(data)
    if form.is_valid():
        model = form.cleaned_data['model']
        cd = form.cleaned_data
        model.update_status(state=cd['state'], error=cd.get('error'),
                            traceback=cd.get('traceback'),
                            sp_results=cd.get('sp_results'),
                            detailed_results=cd.get('detailed_results'),
                            model_params=cd.get('model_params'))
        # ^^^ Why is model_params being passed an argument here?
        # If you look at job/models.py, you see that update_status
        # affects traceback, error, and quantiles only. 
        if model.model_name == 'TSNE':
            model.model_params = cd.get('model_params')
            model.save()
        if not model.pass_requirements_for_worker_processing():
            return HttpResponseForbidden(json.dumps({
                'status': 'fail', 'problem': 'User out of time'
            }), content_type="application/json")
        return HttpResponse(json.dumps({'status': 'success'}),
                            content_type="application/json")
    return HttpResponseBadRequest(json.dumps({'status': 'fail',
                                              'problem': form.errors}),
                                  content_type="application/json")


@csrf_exempt
@require_POST
@worker_api
def worker_ensemble_state_view(request, data):
    form = TrainEnsembleStatusForm(data)
    if form.is_valid():
        ensemble = form.cleaned_data['ensemble']
        cd = form.cleaned_data
        ensemble.update_status(traceback=cd.get('traceback'),
                               error=cd.get('error'),
                               quantiles=cd.get('quantiles'))
        if not ensemble.pass_requirements_for_worker_processing():
            return HttpResponseForbidden(json.dumps({
                'status': 'fail', 'problem': 'User out of time'
            }), content_type="application/json")
        return HttpResponse(json.dumps({'status': 'success'}),
                            content_type="application/json")
    return HttpResponseBadRequest(json.dumps({'status': 'fail',
                                              'problem': form.errors}),
                                  content_type="application/json")


@csrf_exempt
@require_POST
@worker_api
def worker_predict_ensemble_state_view(request, data):
    form = PredictEnsembleStatusForm(data)
    if form.is_valid():
        ensemble = form.cleaned_data['ensemble']
        cd = form.cleaned_data
        ensemble.update_status(cd['time'], cd.get('traceback'),
                               cd.get('error'), cd.get('results'))
        return HttpResponse(json.dumps({'status': 'success'}),
                            content_type="application/json")
    return HttpResponseBadRequest(json.dumps({'status': 'fail',
                                              'problem': form.errors}),
                                  content_type="application/json")


#for convnet
#TODO: replace it with normal api
@require_GET
@worker_api
def worker_model_stats(request, data):
    model = data.get('model')
    if not model:
        return HttpResponseBadRequest(
            json.dumps({'status': 'fail'}),
            content_type="application/json"
        )
    try:
        data = LearnModel.objects.get(pk=model)\
            .stats.live().latest('iteration').data
    except:
        return HttpResponseBadRequest(
            json.dumps({'status': 'fail'}),
            content_type="application/json"
        )
    return HttpResponse(json.dumps(data), content_type='application/json')
