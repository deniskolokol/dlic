from django.conf.urls import patterns, url

urlpatterns = patterns(
    'data_management.views',
    url(r'^parsed/(?P<datafile_id>\d+)/$', 'parsed', name='dm_parsed'),
    url(r'^deleted/(?P<datafile_id>\d+)/$', 'deleted', name='dm_deleted'),
    url(r'^parse-notify/$', 'parse_notify', name='parse_notify'),
    url(r'^parse-collect/$', 'parse_collect', name='parse_collect'),
)
