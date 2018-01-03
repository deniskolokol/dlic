import json
from zipfile import is_zipfile
from django.forms.util import ValidationError
from django.forms.fields import Field
from django.core.files.uploadedfile import UploadedFile


class JSONFormField(Field):
    def clean(self, value):
        if not value and not self.required:
            return None
        value = super(JSONFormField, self).clean(value)
        if isinstance(value, basestring):
            try:
                json.loads(value)
            except ValueError:
                raise ValidationError("Enter valid JSON")
        return value


class ZipFileField(Field):
    def __init__(self, max_size, *args, **kwargs):
        self.max_size = max_size
        super(ZipFileField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and not self.required:
            return None
        value = super(ZipFileField, self).clean(value)
        if isinstance(value, UploadedFile) and \
           value.size <= self.max_size \
           and is_zipfile(value):
            return value
        raise ValidationError('Not a zip file.')
