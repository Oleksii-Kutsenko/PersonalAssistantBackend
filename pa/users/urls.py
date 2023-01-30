"""
Users app urls
"""
from django.urls import include, re_path

# pylint: disable=invalid-name
urlpatterns = [
    re_path(r"^api/", include("rest_auth.urls")),
    re_path(r"^api/registration/", include("rest_auth.registration.urls")),
]
