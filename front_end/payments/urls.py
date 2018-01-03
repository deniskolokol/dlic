from django.conf.urls import patterns, url

urlpatterns = patterns(
    'payments.views',
    url(r'^$', 'index', name='payments_index'),
    url(r'^charge/$', 'charge', name='payments_charge'),
    url(r'^save/$', 'save_card', name='payments_save'),
)
