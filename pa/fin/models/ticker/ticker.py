"""
Ticker and hard related models
"""
from datetime import date, timedelta

from django.db import models
from django.db.models import DecimalField, Q

from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES


class OutdatedTickersManager(models.Manager):
    """
    Returns outdated Tickers
    """

    def get_queryset(self):
        """
        Returns queryset which contains Ticker models without information about sector, industry,
         country or outdated ticker statements
        """
        queryset = super().get_queryset()
        quarter_ago = date.today() - timedelta(30 * 3)
        return queryset \
            .filter(Q(sector=Ticker.DEFAULT_VALUE) |
                    Q(industry=Ticker.DEFAULT_VALUE) |
                    Q(country=Ticker.DEFAULT_VALUE) |
                    Q(ticker_statements__name=Statements.net_income.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                    Q(ticker_statements__name=Statements.total_assets.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                    Q(ticker_statements__name=Statements.price.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago)) \
            .order_by('-ticker_statements__fiscal_date_ending')


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    DEFAULT_VALUE = 'Unknown'

    outdated_tickers = OutdatedTickersManager()

    company_name = models.CharField(max_length=100, default=DEFAULT_VALUE)
    country = models.CharField(max_length=50, default=DEFAULT_VALUE)
    industry = models.CharField(max_length=50, default=DEFAULT_VALUE)
    market_cap = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                     null=True)
    price = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    sector = models.CharField(max_length=50, default=DEFAULT_VALUE)
    symbol = models.CharField(max_length=100, unique=True)

    class Meta:
        """
        Model meta class
        """
        indexes = [
            models.Index(fields=['company_name', ]),
            models.Index(fields=['country', ]),
            models.Index(fields=['industry', ]),
            models.Index(fields=['sector', ]),
            models.Index(fields=['symbol', ]),
        ]

    def __str__(self):
        return f"{self.symbol}"


class Statements(models.TextChoices):
    """
    Supported statements
    """
    capital_lease_obligations = 'capital_lease_obligations'
    net_income = 'net_income'
    price = 'price'
    total_assets = 'total_assets'
    short_term_debt = 'short_term_debt'
    total_long_term_debt = 'total_long_term_debt'
    total_revenue = 'total_revenue'
    total_shareholder_equity = 'total_shareholder_equity'


class TickerStatement(TimeStampMixin):
    """
    Model that represents ticker financial statements
    """
    name = models.CharField(choices=Statements.choices, max_length=50)
    fiscal_date_ending = models.DateField()
    value = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE, null=False,
                               related_name='ticker_statements')
