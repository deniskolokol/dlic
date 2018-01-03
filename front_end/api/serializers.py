from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from rest_framework import serializers
from data_management.models import DataFile, ParseLog, DataSet
from job.models import TrainEnsemble, LearnModel, PredictEnsemble
from api.validators import DatasetFilterValidator, model_params_validator
from api.model_settings_rest import SETTINGS
from core.utils import make_random_str, build_key


class AdminFieldsMixin(object):
    def __init__(self, *args, **kwargs):
        super(AdminFieldsMixin, self).__init__(*args, **kwargs)
        try:
            is_superuser = kwargs['context']['request'].user.is_superuser
        except KeyError:
            is_superuser = False
        if not is_superuser:
            for field_name in self.Meta.admin_fields:
                del self.fields[field_name]


class JSONSerializerField(serializers.WritableField):
    def to_native(self, obj):
        return obj

    def from_native(self, data):
        return data


class PredictEnsembleSerializer(AdminFieldsMixin, serializers.ModelSerializer):
    results = JSONSerializerField(read_only=True)

    class Meta(object):
        model = PredictEnsemble
        fields = ('id', 'state', 'error', 'results', 'iterations',
                  'predicting_time', 'traceback', 'input_data', 'dataset')
        read_only_fields = ('id', 'state', 'error', 'iterations',
                            'predicting_time', 'traceback')
        admin_fields = ('traceback', )

    def get_related_field(self, model_field, related_model, to_many):
        if model_field and self.context and model_field.name == 'dataset':
            user = self.context['request'].user
            qs = related_model._default_manager.visible_to(user)
            return serializers.PrimaryKeyRelatedField(queryset=qs,
                                                      many=to_many,
                                                      required=False)
        return super(PredictEnsembleSerializer, self).get_related_field(
            model_field, related_model, to_many
        )

    def validate(self, attrs):
        input_data = attrs.get('input_data')
        dataset = attrs.get('dataset')
        if input_data is not None and dataset is not None:
            raise serializers.ValidationError(
                "input_data and dataset field mustn't be used together."
            )
        if input_data is not None:
            attrs['input_data'] = input_data.strip()
        return attrs


class TrainEnsembleSerializer(AdminFieldsMixin, serializers.ModelSerializer):
    total_time = serializers.SerializerMethodField('get_total_time')
    models_count = serializers.SerializerMethodField('get_models_count')
    train_dataset_name = \
        serializers.SerializerMethodField('get_train_dataset_name')
    test_dataset_name = \
        serializers.SerializerMethodField('get_test_dataset_name')
    state = serializers.Field('get_state_display')

    class Meta(object):
        model = TrainEnsemble
        fields = ('id', 'shared', 'created', 'data_type',
                  'send_email_on_change', 'net_type',
                  'train_dataset', 'state', 'models_count', 'total_time',
                  'test_dataset', 'train_dataset_name', 'test_dataset_name',
                  'traceback')
        read_only_fields = ('id', 'shared', 'created', 'net_type',
                            'data_type', 'traceback')
        admin_fields = ('traceback', )

    def get_related_field(self, model_field, related_model, to_many):
        if model_field and self.context and \
           model_field.name in ('train_dataset', 'test_dataset'):
            user = self.context['request'].user
            qs = related_model._default_manager.visible_to(user)
            required = model_field.name == 'train_dataset'
            return serializers.PrimaryKeyRelatedField(queryset=qs,
                                                      many=to_many,
                                                      required=required)
        return super(TrainEnsembleSerializer, self).get_related_field(
            model_field, related_model, to_many
        )

    def get_models_count(self, obj):
        try:
            return obj.models_count
        except AttributeError:
            return 0

    def get_total_time(self, obj):
        try:
            return obj.total_time
        except AttributeError:
            return 0

    def get_train_dataset_name(self, obj):
        try:
            return obj.train_dataset.name
        except AttributeError:
            return None

    def get_test_dataset_name(self, obj):
        try:
            return obj.test_dataset.name
        except AttributeError:
            return None

    def validate_test_dataset(self, attrs, source):
        test_dataset = attrs.get(source)
        train_dataset = attrs.get('train_dataset')

        if not test_dataset and self.object:
            #TODO: why?
            test_dataset = self.object.test_dataset

        if not train_dataset and self.object:
            train_dataset = self.object.train_dataset

        if train_dataset and test_dataset:

            test_format = test_dataset.data.file_format
            train_format = train_dataset.data.file_format

            if test_format != train_format:
                message = 'Test and train dataset should be of the same type'
                raise serializers.ValidationError(message)
        return attrs

    def validate(self, attrs):
        train_dataset = attrs.get('train_dataset')
        test_dataset = attrs.get('test_dataset')
        if train_dataset is not None and \
           test_dataset is None and \
           train_dataset.data.file_format != 'GENERAL':
            raise serializers.ValidationError(
                {"test_dataset": ["This field is required."]}
            )
        return attrs


class ParseLogSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = ParseLog
        fields = ('id', 'timestamp', 'message')
        read_only_fields = ('id', 'timestamp', 'message')


class DataSetIdNameSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = DataSet
        fields = ('id', 'name', 'last_column_is_output', 'filters')
        read_only_fields = ('id', 'name', 'last_column_is_output', 'filters')


class DataFileCreateSerializer(serializers.Serializer):
    TIMESERIES = 'TIMESERIES'
    GENERAL = 'GENERAL'
    FORMAT_CHOICES = (
        (TIMESERIES, 'Timeseries'),
        (GENERAL, 'General'),
    )
    name = serializers.CharField(required=False)
    file = serializers.FileField(required=False)
    data = serializers.CharField(required=False, min_length=1)
    file_format = serializers.ChoiceField(required=False,
                                          choices=FORMAT_CHOICES)

    def restore_object(self, attrs, instance=None):
        user = self.context['view'].request.user
        if attrs.get('data'):
            name = attrs['name']
            ext = {'TIMESERIES': '.ts', 'GENERAL': '.csv'}
            ext = ext[attrs['file_format']]
            file = SimpleUploadedFile(make_random_str() + ext,
                                      attrs['data'].encode('utf-8'))
        else:
            file = attrs['file']
            name = attrs.get('name')
            if not name:
                name = file.name
        key = build_key(user.pk, file.name)
        if not file.name.lower().endswith(settings.DATA_FILE_PLAIN_EXT):
            key += '.zip'
        return DataFile(bucket=settings.S3_BUCKET, key=key,
                        user=user, name=name, local_file=file,
                        state=DataFile.STATE_UPLOADED)

    def validate(self, attrs):
        data = attrs.get('data')
        file = attrs.get('file')
        name = attrs.get('name')
        file_format = attrs.get('file_format')
        if not data and not file:
            raise serializers.ValidationError(
                'Data or file field is required.')
        if data:
            if not name:
                raise serializers.ValidationError('Name field is required '
                                                  'with data field.')
            elif not file_format:
                raise serializers.ValidationError('File format field is '
                                                  'required with data field.')
        else:
            if not file.name.lower().endswith(settings.DATA_FILE_EXT):
                raise serializers.ValidationError({
                    'file': [
                        'Not supported file extension. Supported extensions: '
                        '%s' % ', '.join(settings.DATA_FILE_EXT)
                    ]
                })
        return attrs


class DataFileSerializer(serializers.ModelSerializer):
    parse_logs = ParseLogSerializer(many=True, required=False, read_only=True)
    datasets = serializers.SerializerMethodField('get_datasets')
    meta = serializers.SerializerMethodField('get_meta')
    state = serializers.Field('get_state_display')

    class Meta(object):
        model = DataFile
        fields = ('id', 'created', 'shared', 'name', 'parse_logs', 'datasets',
                  'meta', 'state', 'file_format')
        read_only_fields = ('id', 'created', 'shared', 'file_format')

    def get_meta(self, obj):
        meta = obj.meta or {}
        try:
            del meta['key']
        except KeyError:
            pass
        return meta

    def get_datasets(self, obj):
        #TODO: Fix this when you will use django 1.7, use Prefetch
        user = self.context['request'].user
        qs = obj.datasets.all()
        qs = [dset for dset in qs if dset.is_visible_to(user)]
        serializer = DataSetIdNameSerializer(many=True, instance=qs)
        return serializer.data


class DataSetSerializer(serializers.ModelSerializer):
    filters = JSONSerializerField(required=False)

    class Meta(object):
        model = DataSet
        fields = ('id', 'created', 'shared', 'data', 'filters', 'name',
                  'last_column_is_output')
        read_only_fields = ('id', 'created', 'shared')

    def get_related_field(self, model_field, related_model, to_many):
        if model_field and model_field.name == 'data' and self.context:
            user = self.context['request'].user
            qs = related_model._default_manager.visible_to(user)\
                .filter(state=DataFile.STATE_READY)
            return serializers.PrimaryKeyRelatedField(queryset=qs,
                                                      many=to_many,
                                                      required=True)
        return super(DataSetSerializer, self).get_related_field(model_field,
                                                                related_model,
                                                                to_many)

    def validate(self, attrs):
        filters = attrs.get('filters')
        if filters:
            validator = DatasetFilterValidator(attrs['data'], filters)
            validator.validate()
        if attrs['data'].file_format == attrs['data'].GENERAL:
            if attrs.get('last_column_is_output') is None:
                raise serializers.ValidationError({
                    u'last_column_is_output': [u'This field is required.']
                })
            try:
                classes = attrs['data'].meta['last_column_info']['classes']
            except (AttributeError, KeyError, TypeError):
                raise serializers.ValidationError({'data': "Invalid format"})
            if classes is None and attrs['last_column_is_output']:
                error = ("Last column should contains "
                         "only integers, started from 0")
                raise serializers.ValidationError(
                    {'last_column_is_output': [error]}
                )
        return attrs


class LearnModelSerializer(AdminFieldsMixin, serializers.ModelSerializer):
    model_params = JSONSerializerField()

    class Meta(object):
        model = LearnModel
        fields = ('id', 'ensemble', 'model_name', 'model_params', 'created',
                  'updated', 'state', 'training_time', 'traceback', 'name',
                  'training_logs')
        read_only_fields = ('id', 'created', 'updated', 'state',
                            'training_time', 'traceback', 'training_logs')
        admin_fields = ('traceback', )

    def validate_model_name(self, attrs, source):

        """
        Raise validation error if ensemble type not equal model type
        """

        ensemble = attrs.get('ensemble')
        #TODO: fix this, ensemble not required because of patch
        if ensemble:
            type = ensemble.data_type
            if type == TrainEnsemble.IMAGES and attrs[source] != 'CONV':
                raise serializers.ValidationError('Ensemble and model use '
                                                  'different type of data')

            if type == TrainEnsemble.TIMESERIES and attrs[source] != 'MRNN':
                raise serializers.ValidationError('Ensemble and model use '
                                                  'different type of data')

            if type == TrainEnsemble.GENERAL and attrs[source] in ['CONV',
                                                                   'MRNN']:
                raise serializers.ValidationError('Ensemble and model use '
                                                  'different type of data')

            l = LearnModel.objects.live() \
                .filter(ensemble=attrs['ensemble'])[:1]

            if l:
                if attrs[source] != l[0].model_name:
                    message = 'Model name not valid. All models type should ' \
                              'be the same({0})'.format(l[0].model_name)
                    raise serializers.ValidationError(message)
            if not ensemble.test_dataset and attrs[source] != 'AUTOENCODER' \
                and attrs[source] != 'TSNE':
                raise serializers.ValidationError('For this model, ensemble '
                                                  'must have a test dataset')
        return attrs

    def validate(self, attrs):
        """
        Validate json params, only allow valid params.
        """

        # TODO: it's a totaly mess, review and refactoring required
        if 'model_params' in attrs:
            params = attrs['model_params']
            if self.object:
                setting = SETTINGS.get(self.object.model_name)
            else:
                setting = SETTINGS.get(attrs['model_name'])
            if not setting:
                setting = SETTINGS.get('MRNN')
            model_params_validator(params, setting)
        return attrs
