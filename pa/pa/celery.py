"""
Root module for file celery application
"""
import os

import redis
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pa.settings')

# pylint: disable=invalid-name
app = Celery('pa', include=['fin.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

redis_client = redis.Redis(host='redis', port=6379)
