from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib import admin
from web.forms import SignupForm, SigninForm
admin.autodiscover()

urlpatterns = patterns(
    'web.views',
    url(r'^$', 'home', name='home'),
    url(r'^sign_up/$', 'sign_up', name='sign_up'),
    url(r'^register/$', 'register', name='register'),
    url(r'^dashboard/$', 'dashboard_index', name="dashboard_main"),
    url(r'^dashboard/data-wizard/\d+/$', 'dashboard_index'),
    url(r'^dashboard/ensemble-wizard/\d+/step/\w+-\w+/$', 'dashboard_index'),
    url(r'^dashboard/ensembles/$', 'ensembles_index', name="ensembles_main"),
    url(r'^dashboard/user-stats/$', 'dashboard_admin', name='dashboard_admin'),
    url(r'^dashboard/credentials/$', 'dashboard_credentials',
        name='dashboard_credentials'),

    url(r'^train/new/$', 'create_train_ensemble_new',
        name='create_train_ensemble'),
    url(r'^train-ensemble/(?P<pk>\d+)/$', 'view_train_ensemble',
        name='view_train_ensemble'),
    url(r'^predict/train-ensemble/(?P<train_ensemble_pk>\d+)/$',
        'create_predict_ensemble', name='create_predict_ensemble'),
    url(r'^download/', 'download_from_s3'),

    url(r'^bd_admin/', include(admin.site.urls)),
    url(r'^api/', include('api.urls')),
    url(r'^data/', include('data_management.urls')),
    url(r'^payments/', include('payments.urls')),
    url(r'^help/', include('help.urls')),
    url(r'^api-help/', include('rest_framework_swagger.urls')),
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(r'^login/$', 'login', {'extra_context': {'signup_form': SignupForm()},
                               'authentication_form': SigninForm},
        name='login'),
    url(r'^logout/$', 'logout', {'next_page': '/'}, name='logout'),
    url(r'^password_reset/$', 'password_reset', name='password_reset'),
    url(r'^password_reset/done/$', 'password_reset_done',
        name='password_reset_done'),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'password_reset_confirm', name='password_reset_confirm'),
    url(r'^reset/done/$', 'password_reset_complete',
        name='password_reset_complete'),
)

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
