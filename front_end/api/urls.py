from django.conf.urls import patterns, url
from api import views
from rest_framework.routers import DefaultRouter

urlpatterns = patterns(
    'api.views',
    #----worker----
    url(r'^stats/$', 'stats_view', name='api_stats'),
    url(r'^logs/$', 'logs_view', name='api_logs'),
    url(r'^dataset/update/$', 'dataset_patch'),
    url(r'^ensemble/status/$', 'worker_ensemble_state_view',
        name='api_ensemble_status'),
    url(r'^predict-ensemble/status/$', 'worker_predict_ensemble_state_view',
        name='api_predict_ensemble_status'),
    url(r'^train/status/$', 'worker_job_state_view', name='api_train_status'),
    url(r'^worker/model/stats/$', 'worker_model_stats',
        name='worker_model_stats'),
)

router = DefaultRouter()
router.register(r'ensemble', views.EnsembleViewSet, base_name='ensemble')
router.register(r'model', views.LearnModelViewSet, base_name='model')
router.register(r'data', views.DataViewSet, base_name='data')
router.register(r'dataset', views.DataSetViewSet, base_name='dataset')
router.register(r'predict', views.PredictViewSet, base_name='predict')
urlpatterns += router.urls
