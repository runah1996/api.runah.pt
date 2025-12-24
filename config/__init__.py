"""
Celery app initialization for api.runah.pt
"""

from .celery import app as celery_app

__all__ = ('celery_app',)

