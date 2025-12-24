"""
Celery configuration for api.runah.pt
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('api_runah')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule - runs every minute
app.conf.beat_schedule = {
    'refresh-csgonet-cases-every-minute': {
        'task': 'public.tasks.refresh_csgonet_cases',
        'schedule': crontab(minute='*/1'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

