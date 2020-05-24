from django.db import models
from django.db.models import DateTimeField


class TimeStampMixin(models.Model):
    """
    Mixin for created, updated fields
    """
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)

    class Meta:
        """Meta"""
        abstract = True
