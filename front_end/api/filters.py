import json
from django.db.models import Q
from rest_framework import filters
from job.models import TrainEnsemble, LearnModelStat
from data_management.models import DataSet


class EnsembleFilterBackend(filters.DjangoFilterBackend):
    """
    Filtering by dataset query param
    Returns all ensembles which use this dataset as train/test/valid
    """

    def filter_queryset(self, request, queryset, view):
        qs = super(EnsembleFilterBackend, self).filter_queryset(request,
                                                                queryset,
                                                                view)
        dataset = request.QUERY_PARAMS.get('dataset')
        data = request.QUERY_PARAMS.get('data')
        if dataset:
            try:
                qs = qs.filter(Q(train_dataset=dataset) |
                               Q(test_dataset=dataset) |
                               Q(valid_dataset=dataset))
            except ValueError:
                pass
        elif data:
            try:
                qs = qs.filter(Q(train_dataset__data=data) |
                               Q(test_dataset__data=data) |
                               Q(valid_dataset__data=data))
            except ValueError:
                pass
        return qs


class DataSetFilterBackend(filters.DjangoFilterBackend):
    """
    Filtering by for_ensemble query param
    Returns all dataset which could be used as train or test for ensemble
    """

    def _filter_for_ensemble(self, request, queryset, view,
                             for_ensemble, with_output):
        try:
            ensemble = TrainEnsemble.objects.visible_to(request.user)\
                .get(pk=for_ensemble)
        except:
            return queryset
        qs = DataSet.objects.visible_to(request.user) \
            .filter(data__file_format=ensemble.data_type)
        train_dset = ensemble.train_dataset
        if train_dset is None:
            dset_ids = qs.values_list('id', flat=True)
        else:
            qs = qs.values('id', 'data__meta', 'last_column_is_output')
            dset_ids = []
            for dset in qs:
                try:
                    meta = json.loads(dset.pop('data__meta'))
                except (ValueError, TypeError):
                    meta = None
                try:
                    last_column_is_output = dset.pop('last_column_is_output')
                except (ValueError, TypeError):
                    last_column_is_output = None
                if train_dset.eq_format(meta, last_column_is_output,
                                        with_output):
                    dset_ids.append(dset['id'])
        return queryset.filter(id__in=dset_ids)

    def filter_queryset(self, request, queryset, view):
        queryset = super(DataSetFilterBackend, self).filter_queryset(request,
                                                                     queryset,
                                                                     view)
        for_ensemble = request.QUERY_PARAMS.get('for_ensemble')
        with_output = not request.QUERY_PARAMS.get('equal_input')
        if for_ensemble:
            queryset = self._filter_for_ensemble(request, queryset,
                                                 view, for_ensemble,
                                                 with_output)
        return queryset


class PredictFilterBackend(filters.DjangoFilterBackend):
    """
    Filtering by ensemble query param
    Returns all predicts which belongs to this ensemble
    """

    def _filter_ensemble(self, request, queryset, view, ensemble):
        return queryset.filter(
            iterations__in=LearnModelStat.objects.filter(
                model__ensemble_id=ensemble
            )
        )

    def filter_queryset(self, request, queryset, view):
        queryset = super(PredictFilterBackend, self).filter_queryset(request,
                                                                     queryset,
                                                                     view)
        ensemble = request.QUERY_PARAMS.get('ensemble')
        if ensemble:
            queryset = self._filter_ensemble(request, queryset, view, ensemble)
        return queryset
