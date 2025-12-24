"""
WebSocket URL routing for public API
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/giveaway/$', consumers.GiveawayConsumer.as_asgi()),
]

