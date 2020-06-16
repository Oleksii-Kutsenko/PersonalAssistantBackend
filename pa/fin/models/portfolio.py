from django.db import models
from django.db.models import ForeignKey, CASCADE, ManyToManyField, IntegerField, CharField, DecimalField
from django.utils.translation import gettext_lazy as _

from fin.models.index import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES
from users.models import User


class Portfolio(TimeStampMixin):
    name = CharField(max_length=100)
    tickers = ManyToManyField(Ticker, through='PortfolioTickers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)


class PortfolioTickers(TimeStampMixin):
    portfolio = ForeignKey(Portfolio, on_delete=CASCADE, related_name='portfolio')
    ticker = ForeignKey(Ticker, on_delete=CASCADE, related_name='portfolio_ticker')
    amount = IntegerField()


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
    portfolio = ForeignKey(Portfolio, related_name='accounts', on_delete=models.CASCADE, null=False)
    value = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
