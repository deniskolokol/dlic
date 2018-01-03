from django import forms
from job.models import (LearnModel, TrainEnsemble,
                        PredictEnsemble, LEARN_MODELS)
from job.model_settings import get_settings_form
from api.fields import JSONFormField


class BaseWorkerApiForm(forms.Form):
    ensemble_fk = ''
    queue_key = forms.CharField(max_length=40)

    def clean(self):
        cleaned_data = super(BaseWorkerApiForm, self).clean()
        if self.errors:
            return cleaned_data
        if self.ensemble_fk:
            queue_key = cleaned_data[self.ensemble_fk].ensemble.queue_key
        else:
            queue_key = cleaned_data['ensemble'].queue_key
        if queue_key != cleaned_data.get('queue_key'):
            raise forms.ValidationError("Queue key doesn't match")
        return cleaned_data


class NameBasedModelFrom(BaseWorkerApiForm):

    def __init__(self, data, *args, **kwargs):
        self.learn_model_cls = LEARN_MODELS.get(data.get('model_name'),
                                                LearnModel)
        super(NameBasedModelFrom, self).__init__(data, *args, **kwargs)

    def clean_model(self):
        model = self.cleaned_data['model']
        if not type(model) is self.learn_model_cls:
            raise forms.ValidationError('Specify correct model_name')
        return model


class LearnModelStatForm(NameBasedModelFrom):
    ensemble_fk = 'model'
    model = forms.ModelChoiceField(queryset=LearnModel.objects.none())
    data = JSONFormField()
    s3_data = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(LearnModelStatForm, self).__init__(*args, **kwargs)
        queryset = self.learn_model_cls.objects.select_for_update() \
            .live().filter(state='TRAIN')
        self.fields['model'] = forms.ModelChoiceField(queryset=queryset)

    def clean_data(self):
        data = self.cleaned_data['data']
        if not isinstance(data.get('iteration'), int):
            raise forms.ValidationError('Wrong value for iteration')
        if not isinstance(data.get('test_accuracy'), float):
            raise forms.ValidationError('Wrong value for test_accuracy')
        if not isinstance(data.get('train_accuracy'), float):
            raise forms.ValidationError('Wrong value for train_accuracy')
        return data


class LearnModelStatusForm(NameBasedModelFrom):
    ensemble_fk = 'model'
    model = forms.ModelChoiceField(queryset=LearnModel.objects.none())
    state = forms.ChoiceField(choices=(('TRAIN', ''),
                                       ('ERROR', ''),
                                       ('CANCELED', ''),
                                       ('FINISHED', ''))
                              )
    error = forms.CharField(max_length=255, required=False)
    traceback = forms.CharField(required=False)
    sp_results = forms.CharField(required=False)
    detailed_results = forms.CharField(required=False)
    model_params = JSONFormField(required=False)

    def __init__(self, *args, **kwargs):
        super(LearnModelStatusForm, self).__init__(*args, **kwargs)
        self.fields['model'] = forms.ModelChoiceField(
            queryset=self.learn_model_cls.objects.live().filter(
                state__in=('NEW', 'QUEUE', 'TRAIN')
            )
        )

    def clean(self):
        cleaned_data = super(LearnModelStatusForm, self).clean()
        if self.errors:
            return cleaned_data
        model = cleaned_data['model']
        if (type(model) is LearnModel and
            cleaned_data.get('state') == 'FINISHED' and
            not (cleaned_data.get('sp_results') and
                 cleaned_data.get('detailed_results'))):
            raise forms.ValidationError("Finished job should set sp_results "
                                        "and detailed results")

        SettingsForm = get_settings_form(model.model_name)
        model_params = cleaned_data['model_params'] or {}
        form = SettingsForm(model_params, model=model, user_update=False)
        if not form.is_valid():
            self._errors = form.errors
        cleaned_data['model_params'] = form.cleaned_data
        return cleaned_data


class TrainEnsembleStatusForm(BaseWorkerApiForm):
    ensemble = forms.ModelChoiceField(queryset=TrainEnsemble.objects.live())
    error = forms.CharField(max_length=255, required=False)
    traceback = forms.CharField(required=False)
    quantiles = forms.CharField(required=False)


class PredictEnsembleStatusForm(BaseWorkerApiForm):
    ensemble = forms.ModelChoiceField(queryset=PredictEnsemble.objects.all())
    time = forms.FloatField(min_value=0.0)
    error = forms.CharField(max_length=255, required=False)
    traceback = forms.CharField(required=False)
    results = JSONFormField(required=False)


class ConvnetFileUploadForm(forms.Form):
    file = forms.ImageField()
