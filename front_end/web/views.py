#coding: utf-8
import json, socket
from functools import wraps
from collections import defaultdict
from hashlib import sha1
from django.core import signing
from django.template import loader
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import login
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage, mail_admins
from django.contrib.sites.models import get_current_site
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Count, Max, Sum, Q
from core.utils import sign_s3_get
from web.forms import SignupForm
from web.models import ApiUser
from api.models import ApiKey
from job.models import (LearnModel, TrainEnsemble,
                        PredictEnsemble, LearnModelStat)
from createsend import Subscriber, Unauthorized



# decorator
def billing_warning(f):
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_paid:
            messages.add_message(request,
                                 messages.WARNING,
                                 'You do not have paid time for '
                                 'training or predictions.')
        return f(request, *args, **kwargs)
    return wrapper


def sign_up(request, signup_form=False):

    sign_up_done = request.session.get('sign_up_done')

    if sign_up_done:
        del request.session['sign_up_done']
    return render(request, 'registration/sign_up.html', {
        'sign_up_done': sign_up_done,
        'signup_form': signup_form if signup_form else SignupForm(),
    })


def home(request):
    extra_context = {}
    if request.GET.get('next'):
        extra_context['next'] = request.GET.get('next')
    extra_context['signup_form'] = SignupForm()
    if not request.user.is_authenticated():
        return login(request, extra_context=extra_context)
    return redirect('dashboard_main')


def register(request, email_template_name='registration/welcome_email.html'):
    if request.method != 'POST':
        return redirect('home')

    signup_form = SignupForm(request.POST)
    if signup_form.is_valid():
        user = ApiUser.objects.create_user(
            email=signup_form.cleaned_data['username'],
            password=signup_form.cleaned_data['password']
        )
        key = '%s:%s:%s' % (user.id,
                            request.session.session_key,
                            'Web.View.Salt')
        key = sha1(key).hexdigest()
        ApiKey.objects.create(user=user, key=key)
        messages.add_message(request,
                             messages.INFO,
                             'New user created, welcome to Ersatz!',
                             fail_silently=False)
        current_site = get_current_site(request)
        opts = {
            'site_name': current_site.name,
            'domain': current_site.domain,
            'protocol': request.is_secure() and 'https' or 'http'
        }
        body = loader.render_to_string(email_template_name, opts)
        email = EmailMessage(subject='Welcome to Ersatz!',
                             body=body,
                             from_email=settings.DEFAULT_FROM_EMAIL,
                             to=(signup_form.cleaned_data['username'],))
        email.send(fail_silently=True)

        if settings.PRODUCTION:
            try:
                c = Subscriber({'api_key': settings.CAMPAIGNMONITOR_KEY})
                username = signup_form.cleaned_data['username']
                c.add(settings.CAMPAIGNMONITOR_LIST, username, username, [],
                      True)
            except (Unauthorized, socket.gaierror), e:
                body = """Error adding email({0}) to campaign monitor.
                List Ersatz beta signup({1}).
                Error:
                  {2}""".format(signup_form.cleaned_data['username'],
                                settings.CAMPAIGNMONITOR_LIST, e)
                mail_admins('Campaign Monitor Error', body, fail_silently=True)
        if request.POST.get('iframe'):
            request.session['sign_up_done'] = True
            return redirect('sign_up')
        login(request, user)
        return redirect('home')
    elif not signup_form.is_valid() and request.POST.get('iframe'):
        return sign_up(request, signup_form)
    else:
        request.method = 'GET'
        return login(request, extra_context={'signup_form': signup_form})


@login_required
def dashboard_index(request):
    return render(request, 'web/index.html', {
        'ws_token': signing.dumps('dashboard_ws_%s' % request.user.pk,
                                  settings.WS_SECRET_KEY,
                                  salt=settings.WS_SALT),
        'ws_salt': settings.WS_SALT,
        'ws_url': settings.WS_SERVER_URL,
        'view': 'data'
    })


@login_required
def ensembles_index(request):
    return render(request, 'web/ensemble_index.html', {'view': 'ensembles'})


@login_required
def dashboard_admin(request):
    if not request.user.is_superuser:
        return redirect('dashboard_main')

    data = defaultdict(dict)

    def fill_data(qs, field, user_field='user', agg_field='count'):
        for val in qs:
            data[val[user_field]][field] = val[agg_field]

    users = ApiUser.objects.all() \
        .annotate(train_ensembles_count=Count('train_ensembles')) \
        .order_by('id')
    finished_scores = LearnModelStat.objects \
        .filter(model__state='FINISHED') \
        .values('model', 'model__ensemble__user') \
        .annotate(best_test=Max('test_accuracy'),
                  best_train=Max('train_accuracy'))
    for score in finished_scores:
        data[score['model__ensemble__user']] \
            .setdefault('avg_test', []).append(score['best_test'])
        data[score['model__ensemble__user']] \
            .setdefault('avg_train', []).append(score['best_train'])

    learn_models_count = TrainEnsemble.objects.all() \
        .values('user').annotate(count=Count('learn_models'))
    fill_data(learn_models_count, 'learn_models_count')
    predict_ensembles_count = PredictEnsemble.objects.all() \
        .values('user').annotate(count=Count('user'))
    fill_data(predict_ensembles_count, 'predict_ensembles_count')
    finished_ensembles = TrainEnsemble.objects.exclude(
        learn_models__in=LearnModel.objects.exclude(state='FINISHED')) \
        .values('user').annotate(count=Count('user'))
    fill_data(finished_ensembles, 'finished_ensembles')
    finished_models = LearnModel.objects \
        .filter(state='FINISHED').values('ensemble__user') \
        .annotate(count=Count('ensemble__user'))
    fill_data(finished_models, 'finished_models', 'ensemble__user')
    finished_ensembles = PredictEnsemble.objects \
        .exclude(state='FINISHED').values('user').annotate(count=Count('user'))
    fill_data(finished_ensembles, 'finished_predict_ensembles')
    training_time = TrainEnsemble.objects.all() \
        .values('user').annotate(summ=Sum('learn_models__training_time'))
    fill_data(training_time, 'training_time', agg_field='summ')
    predicting_time = PredictEnsemble.objects.all() \
        .values('user').annotate(summ=Sum('predicting_time'))
    fill_data(predicting_time, 'predicting_time', agg_field='summ')

    for u in users:
        if u.id not in data:
            u.avg_test = u.avg_train = u.finished_train_ensembles = 0
            u.finished_predict_ensembles = u.finished_models = 0
            u.learn_models_count = u.predict_ensembles_count = 0
            u.training_time = u.predicting_time = 0
            continue
        u.avg_test = sum(data[u.id].get('avg_test', [])) / \
            len(data[u.id].get('avg_test', '0'))
        u.avg_train = sum(data[u.id].get('avg_train', [])) / \
            len(data[u.id].get('avg_train', '0'))
        u.finished_train_ensembles = data[u.id].get('finished_ensembles', 0)
        u.finished_predict_ensembles = data[u.id] \
            .get('finished_predict_ensembles', 0)
        u.finished_models = data[u.id].get('finished_models', 0)
        u.learn_models_count = data[u.id].get('learn_models_count', 0)
        u.predict_ensembles_count = data[u.id] \
            .get('predict_ensembles_count', 0)
        u.training_time = data[u.id].get('training_time', 0)
        u.predicting_time = data[u.id].get('predicting_time', 0)

    return render(request,
                  'web/dashboard_admin.html',
                  {'view': 'admin', 'users': users})


@login_required
def dashboard_credentials(request):
    return render(request, 'web/api_credentials.html', {})


@login_required
@billing_warning
def create_train_ensemble_new(request):
    if not request.user.supported_training_s3files().exists():
        url = reverse('dm_index')
        messages.warning(
            request, 'You must <a href="' + url + '">upload</a> a file first.'
        )
    files = request.user.supported_training_s3files() \
        .values('id', 'format', 'name', 'key')
    files = json.dumps(list(files))
    dataset = request.GET.get('dataset')
    return render(request, 'web/create_train_ensemble.html',
                  {'files': files, 'dataset': dataset})


@login_required
@billing_warning
def create_predict_ensemble(request, train_ensemble_pk):
    try:
        if request.user.is_superuser:
            train_ensemble = TrainEnsemble.objects \
                .live().get(pk=train_ensemble_pk)
        else:
            train_ensemble = TrainEnsemble.objects.live() \
                .filter(Q(user=request.user) | Q(shared=True)) \
                .get(pk=train_ensemble_pk)
    except TrainEnsemble.DoesNotExist:
        raise Http404
    return render(request, 'web/predict_ensemble_new.html',
                  {'train_ensemble': train_ensemble})


@login_required
@billing_warning
def view_train_ensemble(request, pk):
    if request.user.is_superuser:
        ensemble = get_object_or_404(TrainEnsemble, pk=pk, deleted=False)
    else:
        try:
            ensemble = TrainEnsemble.objects \
                .filter(Q(user=request.user) | Q(shared=True), deleted=False) \
                .get(pk=pk)
        except TrainEnsemble.DoesNotExist:
            raise Http404
    return render(request, 'web/train_ensemble.html',
                  {'ensemble': ensemble, 'models': LearnModel.TRAIN_MODELS})


def download_from_s3(request):
    """
    Use request path as s3 key, sign it and redirct user to s3
    WARNING: any keys which has prefix /download/ could be downloaded
    by anyone, be careful
    """
    url = sign_s3_get(request.path)
    return redirect(url)
