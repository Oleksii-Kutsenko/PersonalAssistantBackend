"""
URLs
"""
from django.conf.urls import url
from django.urls import include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from fin import views

router = routers.DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'indices', views.IndexViewSet)
router.register(r'goals', views.GoalViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="PA.FIN API",
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api/indices/(?P<index_id>[1-9][0-9]*)/adjusted/$',
        views.AdjustedIndex.as_view(),
        name='index-adjusted'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
