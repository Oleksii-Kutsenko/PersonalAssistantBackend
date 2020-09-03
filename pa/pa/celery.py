"""
Root module for file celery application
"""
import logging
import os
from contextlib import contextmanager

import redis
from celery import Celery

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pa.settings')

app = Celery('pa', include=['fin.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

redis_client = redis.Redis(host='redis', port=6379)
