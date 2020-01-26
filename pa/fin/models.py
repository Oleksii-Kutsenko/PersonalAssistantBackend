from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampMixin(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")
        EUR = 'EUR', _("Euro")

    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, choices=Currency.choices)


class Record(TimeStampMixin):
    amount = models.IntegerField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
