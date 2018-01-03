from django.db import models
from django.conf import settings


class ApiKey(models.Model):
    key = models.CharField(
        max_length=40, unique=True, verbose_name='User api key'
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)

    def __unicode__(self):
        return self.key
