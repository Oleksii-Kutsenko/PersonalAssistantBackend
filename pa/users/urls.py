"""
Users app urls
"""
from django.conf.urls import url
from django.urls import include

# pylint: disable=invalid-name
urlpatterns = [
    url(r'^api/', include('rest_auth.urls')),
    url(r'^api/registration/', include('rest_auth.registration.urls')),
]
