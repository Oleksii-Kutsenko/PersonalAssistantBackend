"""
Websocket routing for FIN module
"""
from django.urls import re_path

from . import websocket

websocket_urlpatterns = [
    re_path(r'ws/fin/api/indices/(?P<index_id>[1-9][0-9]*)/adjusted/$',
            websocket.AdjustedIndexConsumer),
]
