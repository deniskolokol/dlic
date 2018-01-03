from .models import ApiKey
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class UseKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.GET.get('key') or request.POST.get('key')
        if not key:
            return None
        try:
            api_key = ApiKey.objects.select_related('user').get(key=key)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Username or key not valid")
        return (api_key.user, None)
