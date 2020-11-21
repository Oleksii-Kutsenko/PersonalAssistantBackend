"""
Helpers for models
"""
from django.db import models
from django.db.models import DateTimeField
from django.utils.translation import gettext_lazy as _


class TimeStampMixin(models.Model):
    """
    Mixin for created, updated fields
    """
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)

    class Meta:
        """
        Model meta class
        """
        abstract = True


MAX_DIGITS = 19
DECIMAL_PLACES = 2


class UpdatingStatus(models.IntegerChoices):
    """
    Update statuses for models with tickers
    """
    successfully_updated = 0, _('Successfully Updated')
    updating = 1, _('Updating')
    update_failed = 2, _('Update Failed')
