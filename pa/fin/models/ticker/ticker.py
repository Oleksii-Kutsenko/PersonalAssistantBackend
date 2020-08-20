"""
Ticker and hard related models
"""
from django.db import models
from django.db.models import DecimalField

from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    DEFAULT_VALUE = 'Unknown'

    company_name = models.CharField(max_length=50, default=DEFAULT_VALUE)
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
