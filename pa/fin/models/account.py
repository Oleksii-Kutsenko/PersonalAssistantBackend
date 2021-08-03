"""
Account and related models
"""
from django.db import models
from django.db.models import CharField, ForeignKey, DecimalField
from django.utils.translation import gettext_lazy as _

from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        """
        Available currencies for account
        """
        CAD = 'CAD', _('Canadian Dollar')
        CHF = 'CHF', _('Swiss franc')
        EUR = 'EUR', _("Euro")
        GBP = 'GBP', _('Pound sterling')
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")

    name = CharField(max_length=100)
    currency = CharField(max_length=3, choices=Currency.choices)
    portfolio = ForeignKey('Portfolio', related_name='accounts', on_delete=models.CASCADE, null=False)
    value = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)

    class Meta:
        """
        Model meta class
        """
        constraints = [
            models.UniqueConstraint(fields=['currency', 'portfolio_id'], name='currency_portfolio_id_unique')
        ]
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['currency', ]),
        ]
