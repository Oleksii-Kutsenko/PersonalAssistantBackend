"""
Models
"""
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import DecimalField, IntegerField, CharField
from django.utils.translation import gettext_lazy as _

from fin.models.utils import TimeStampMixin

MAX_DIGITS = 19
DECIMAL_PLACES = 2


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        """
        Available currencies for account
        """
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")
        EUR = 'EUR', _("Euro")

    name = CharField(max_length=100)
    currency = CharField(max_length=3, choices=Currency.choices)


class Record(TimeStampMixin):
    """
    Record model
    """
    amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)


class Goal(TimeStampMixin):
    """
    Goal model
    """
    name = CharField(max_length=100)
    coefficient = DecimalField(max_digits=3, decimal_places=DECIMAL_PLACES,
                               validators=[MinValueValidator(0.000001),
                                           MaxValueValidator(1.000001)])
    level = IntegerField(validators=[MinValueValidator(1)])
    current_money_amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                        validators=[MinValueValidator(0)])
    target_money_amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                       validators=[MinValueValidator(1)])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.current_money_amount == self.target_money_amount:
            self.target_money_amount *= (self.coefficient + Decimal(1))
            self.level += 1

        super(Goal, self).save(force_insert=False, force_update=False, using=None,
                               update_fields=None)
