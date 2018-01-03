from django.conf import settings


def version(request):
    return {'code_version': settings.VERSION}

def socketurl(request):
    return {'SOCKET_URL': settings.SOCKET_URL}
