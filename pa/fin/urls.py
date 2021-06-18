"""
URLs
"""
from django.urls import include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions

from fin import views

router = routers.DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'exante-settings', views.ExanteSettingsViewSet)
router.register(r'indices', views.IndexViewSet)
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolios')
router.register(r'portfolio-policies', views.PortfolioPolicyViewSet, basename='portfolio-policies')

SchemaView = get_schema_view(
    openapi.Info(
        title="PA.FIN API",
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r'^api/', include(router.urls)),
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^swagger/$', SchemaView.with_ui('swagger', cache_timeout=0),
            name='schema-swagger-ui'),
]
