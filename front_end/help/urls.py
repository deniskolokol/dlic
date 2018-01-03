from django.conf.urls import patterns, url

urlpatterns = patterns(
    'help.views',
    url(r'^$', 'help_view', {'md': 'index'}, name='help'),
    url(r'^api/$', 'help_view', {'md': 'api_docs'}, name='help_api_docs'),
    url(r'^data/$', 'help_view', {'md': 'data'}),
    url(r'^mrnn/$', 'help_view', {'md': 'mrnn'}),
    url(r'^mrnn-example/$', 'help_view', {'md': 'mrnn_example'}),
    url(r'^autoencoder/$', 'help_view', {'md': 'autoencoder'}),
    url(r'^cnn/$', 'help_view', {'md': 'convnet'}),
)
