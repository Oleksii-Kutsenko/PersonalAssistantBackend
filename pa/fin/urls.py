from django.urls import path, include
from rest_framework import routers
from fin import views

router = routers.DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'indices', views.IndexViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
