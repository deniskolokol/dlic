from django import template
from django.conf import settings
import hmac
import hashlib

register = template.Library()


@register.filter
def intercom_hash(value):
    return hmac.new(settings.INTERCOM_API_SECRET,
                    str(value),
                    digestmod=hashlib.sha256).hexdigest()
