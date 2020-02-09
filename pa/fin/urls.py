from django.conf.urls import url
from django.urls import path, include
from rest_framework import routers
from fin import views

router = routers.DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'indices', views.IndexViewSet)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api/adjusted-index/index/(?P<index_id>[1-9][0-9]*)/$', views.AdjustedIndex.as_view()),
    url(r'api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
