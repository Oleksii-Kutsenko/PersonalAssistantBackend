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


@contextmanager
def redis_lock(lock_id):
    """
    Yield 1 if specified lock_name is not already set in redis. Otherwise returns 0.
    Enables sort of lock functionality.
    """
    status = redis_client.set(lock_id, 'lock', nx=True)
    try:
        yield status
    finally:
        redis_client.delete(lock_id)
