import json
import validictory
from django.core.exceptions import ImproperlyConfigured
from django import forms
from rest_framework import serializers
from data_management.models import DataFile
from job.models import LearnModel, LearnModelStat


class DatasetFilterValidator(object):
    filter_register = {'merge', 'normalize', 'shuffle', 'split',
                       'binarize', 'ignore', 'permute', 'balance', 'outputs'}
    allowed_after = {
        'merge': {'shuffle', 'normalize', 'split', 'balance', 'binarize'},
        'normalize': {'merge', 'shuffle', 'split', 'balance', 'binarize'},
        'shuffle': {'merge', 'normalize', 'split', 'balance', 'binarize'},
        'binarize': {'merge', 'normalize', 'split', 'balance', 'shuffle'},
        'split': {'merge', 'normalize', 'shuffle', 'balance', 'binarize'},
        'balance': {'merge', 'normalize', 'split', 'shuffle', 'binarize'},
        'ignore': {'normalize', 'shuffle', 'merge',
                   'balance', 'permute', 'split'},
        'permute': {'normalize', 'shuffle', 'merge', 'balance', 'split',
                    'outputs'},
        'outputs': {'normalize', 'shuffle', 'merge', 'balance', 'permute',
                    'split'}
    }
    filter_schema = {
        'type': 'array',
        'items': {'type': 'object'}
    }
    shuffle_schema = {
        'type': 'object',
        'properties': {'name': {'type': 'string'}}
    }
    binarize_schema = {
        'type': 'object',
        'properties': {'name': {'type': 'string'}}
    }
    normalize_schema = {
        'type': 'object',
        'properties': {'name': {'type': 'string'}}
    }
    merge_schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'datas': {'type': 'array', 'minItems': 1, 'maxItems': 10}
        }
    }
    split_schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string', 'minLength': 1},
            'start': {'type': 'integer', 'minimum': 0, 'maximum': 99},
            'end': {'type': 'integer', 'minimum': 1, 'maximum': 100}
        }
    }
    ignore_schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'columns': {'type': 'array'}
        }
    }
    permute_schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'columns': {'type': 'array'}
        }
    }
    balance_schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'sample': {'type': 'string'}
        }
    }
    output_schema = {
        'type': "object",
        'properties': {
            "name": {'type': 'string'},
            "columns": {"type": 'array'},
        }
    }
    schemas = {
        'merge': merge_schema,
        'shuffle': shuffle_schema,
        'split': split_schema,
        'normalize': normalize_schema,
        'binarize': binarize_schema,
        'ignore': ignore_schema,
        'permute': permute_schema,
        'balance': balance_schema,
        'outputs': output_schema,
    }

    def __init__(self, data, filters):
        if set(self.schemas.keys()) != self.filter_register or \
           set(self.allowed_after.keys()) != self.filter_register:
            raise ImproperlyConfigured('Dataset filter validator '
                                       'has invalid configuration')
        self.data = data
        self.filters = filters

    def validate(self):
        """
        run all validate methods for filters
        """

        self.validate_type()
        names = self.validate_names()
        self.validate_schemas()
        if 'merge' in names:
            self.validate_merge(self.filters[names.index('merge')], self.data)
        if 'split' in names:
            self.validate_split(self.filters[names.index('split')], self.data)
        if 'outputs' in names:
            self.validate_output(self.filters[names.index('outputs')],
                                 self.filters[names.index('ignore')],
                                 self.data)

    def validate_type(self):
        """
        validate data structure of filters
        filters should be list of dicts
        """

        try:
            validictory.validate(self.filters, self.filter_schema)
        except ValueError:
            raise serializers.ValidationError("invalid format")

    def validate_names(self):
        """
        validate names of filters
        """

        names = []
        for flt in self.filters:
            if 'name' not in flt:
                raise serializers.ValidationError("filter should have name")
            name = flt['name']
            if name not in self.filter_register:
                raise serializers.ValidationError("unknown filter name: %s"
                                                  % name)
            if name in names:
                raise serializers.ValidationError(
                    "found more than one filter with name: %s" % name
                )
            names.append(name)
        return names

    def validate_order(self):
        """
        validate order of filters
        """

        allowed = self.filter_register.copy()
        applied = set()
        for flt in self.filters:
            name = flt['name']
            if name not in allowed:
                raise serializers.ValidationError(
                    "filter %s can't be applied in this order" % name
                )
            allowed &= self.allowed_after[name]
            applied.add(name)
            allowed -= applied

    def validate_schemas(self):
        """
        validates each filter against its schema
        """

        for flt in self.filters:
            try:
                validictory.validate(flt, self.schemas[flt['name']],
                                     disallow_unknown_properties=True)
            except ValueError as exc:
                raise serializers.ValidationError({'filters': {exc.message}})

    def validate_merge(self, merge, source_data):
        def get_meta(file_format, meta):
            if file_format == 'TIMESERIES':
                return (meta['binary_input'], meta['binary_output'],
                        meta['input_size'], meta['output_size'])
            elif file_format == 'GENERAL':
                return (meta['num_columns'], )
            else:
                return ()

        dfs = DataFile.objects.visible_to(source_data.user)\
            .filter(state=DataFile.STATE_READY)\
            .filter(id__in=merge['datas'])
        errors = []
        message = {'filters': [{"merge":  {"datas": errors}}]}
        datas_set = set(merge['datas']) - {source_data.pk}
        if not all(isinstance(x, int) for x in merge['datas']):
            errors.append("The elements of this field must be integers")
            raise serializers.ValidationError(message)
        if len(datas_set) != len(merge['datas']):
            errors.append("The elements of this field must be unique")
            raise serializers.ValidationError(message)
        not_found = set(merge['datas']) - set([df.id for df in dfs])
        if not_found:
            lst = ', '.join(str(x) for x in not_found)
            errors.append("Elements %s not found" % lst)
            raise serializers.ValidationError(message)
        source_meta = get_meta(source_data.file_format, source_data.meta)
        for df in dfs:
            meta = get_meta(df.file_format, df.meta)
            if meta != source_meta:
                raise serializers.ValidationError(
                    'data files #%s and #%s have different structure, '
                    'merge not possible' % (source_data.pk, df.pk)
                )

    def validate_split(self, split, source_data):
        # TODO: validate percentage
        pass

    def validate_output(self, output, ignore, source_data):
        ignored_in_output = [x for x in output['columns'] if x in
                             ignore['columns']]
        if ignored_in_output:
            raise serializers.ValidationError("You can't select an ignored "
                                              "columns({0}) in output columns "
                                              "filter"
                                              .format(ignored_in_output))
        dtypes = source_data.meta['dtypes']
        columns = output['columns']

        not_valid_columns = [x for x in columns if int(x) >= len(dtypes)]
        if not_valid_columns:
            raise serializers.ValidationError("This columns doesn't exist: {0}"
                                              .format(not_valid_columns))

        types = [dtypes[int(i)] for i in columns]
        column_types = dict(zip(columns, types))

        if len(set(types)) > 1 and set(types) != set(['i', 'S']):
            raise serializers.ValidationError("You can't select different "
                                              "types({0}) of columns in output"
                                              " columns filter"
                                              .format(column_types))


def model_params_validator(params, setting):

    top_params = params.keys()

    schema = setting['default']

    f = setting['form']

    f = f(params, model=False, user_update=False)

    errors_tp = {}
    for x in f.visible_fields():
        if x.field.__class__ == forms.IntegerField and x.name in top_params:
            if params[x.name].__class__ in [str, unicode] and \
               len(params[x.name]) > 0:
                errors_tp[x.name] = [u"{0} field should be a number "
                                     u"not string".format(x.name)]

    if errors_tp:
        raise serializers.ValidationError(errors_tp)

    f.is_valid()

    non_valid_fields = f.non_valid_fields(params, schema)
    if non_valid_fields:
        f.errors['invalid model parameters'] = list(non_valid_fields)

    if f.errors:
        raise serializers.ValidationError(f.errors)


def predict_ensemble_iterations_validator(iterations, user):
    if not iterations:
        raise serializers.ValidationError({
            'iterations': 'This field is required.'
        })
    exc = serializers.ValidationError({
        'iterations': 'This field must be a list of integers.'
    })

    if isinstance(iterations, (str, unicode)):
        try:
            iterations = json.loads(iterations)
        except ValueError:
            raise exc
    if not isinstance(iterations, list):
        raise exc
    try:
        iter_ens = LearnModelStat.objects \
            .filter(id__in=iterations) \
            .filter(model__in=LearnModel.objects.visible_to(user)) \
            .values_list('pk', 'model__ensemble_id')
    except ValueError:
        raise exc
    if iter_ens:
        iterations_real, ensembles = zip(*iter_ens)
    else:
        iterations_real = []
    diff = set(iterations) - set(iterations_real)
    if diff:
        raise serializers.ValidationError({'iterations': (
            "Iterations with this ids don't exists: %s" % list(diff)
        )})
    ensembles = set(ensembles)
    if len(ensembles) > 1:
        raise serializers.ValidationError({
            'iterations': "Iterations must be from same train ensemble."
        })
    return iterations_real


def predict_ensemble_data_validator(iterations, input_data, dataset, files):
    if files:
        data_type = LearnModelStat.objects.filter(pk=iterations[0]) \
            .values_list('model__ensemble__data_type', flat=True)[0]
        if data_type != "IMAGES":
            raise serializers.ValidationError(
                "This ensemble can't predict on files."
            )
        return True
    else:
        if input_data is None and dataset is None:
            raise serializers.ValidationError(
                'Provide input_data or dataset field.'
            )
    return False
