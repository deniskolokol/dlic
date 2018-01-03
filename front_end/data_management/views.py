from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from data_management.models import DataFile


def allow_dmworker_only(view):
    """
    @allow_dmworker_only is decorator for limiting access to
    decorated view for allowed ip-addresses only which workers
    are running on
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.META['REMOTE_ADDR'] in settings.DMWORKER_REMOTE_ADDRESSES:
            return view(request, *args, **kwargs)
        else:
            raise Http404()
    return wrapper


@allow_dmworker_only
@csrf_exempt
def parsed(request, datafile_id):
    df = get_object_or_404(DataFile, pk=datafile_id,
                           state=DataFile.STATE_PARSING_META)
    with df.get_celery_result() as result:
        if result.ready():
            data = result.get()
            df.on_parsed(data)
            return HttpResponse(status=200)
        else:
            return HttpResponse(content='Result not ready', status=500)


@allow_dmworker_only
@csrf_exempt
def deleted(request, datafile_id):
    df = get_object_or_404(DataFile, pk=datafile_id)
    df.on_deleted()
    return HttpResponse(status=200)


@allow_dmworker_only
@csrf_exempt
def parse_notify(request):
    task_id = request.POST['task_id']
    msg = request.POST['msg']
    timestamp = request.POST['timestamp']
    df = get_object_or_404(DataFile,
                           celery_task_id=task_id,
                           state=DataFile.STATE_PARSING_META)
    df.parsing_log_add(timestamp, msg)
    return HttpResponse(status=200)


@allow_dmworker_only
@csrf_exempt
def parse_collect(request):
    dfs = DataFile.objects.filter(state=DataFile.STATE_PARSING_META)
    for df in dfs:
        df.check_parsing_status()
    return HttpResponse(status=200)
