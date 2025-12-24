"""
URL configuration for api.runah.pt
"""

from django.urls import path, include

urlpatterns = [
    path('', include('public.urls')),
]
