"""
URL patterns for public API
"""

from django.urls import path
from .views import GiveawayView, HealthView

urlpatterns = [
    path('giveaway/', GiveawayView.as_view(), name='giveaway'),
    path('health/', HealthView.as_view(), name='health'),
]

