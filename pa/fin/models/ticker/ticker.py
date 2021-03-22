"""
Ticker and hard related models
"""
from datetime import date, timedelta

from django.db import models
from django.db.models import Q
from querybuilder.query import Query

from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES


class OutdatedTickersManager(models.Manager):
    """
    Returns outdated Tickers
    """
    use_in_migrations = True

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
                    Q(pe=None) |
                    Q(ticker_statements__name=Statements.net_income.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                    Q(ticker_statements__name=Statements.total_assets.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                    Q(ticker_statements__name=Statements.price.value,
                      ticker_statements__fiscal_date_ending__lte=quarter_ago)) \
            .order_by('-ticker_statements__fiscal_date_ending') \
            .distinct()


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    DEFAULT_VALUE = 'Unknown'

    objects = models.Manager()
    outdated_tickers = OutdatedTickersManager()

    company_name = models.CharField(max_length=100, default=DEFAULT_VALUE)
    country = models.CharField(max_length=50, default=DEFAULT_VALUE)
    industry = models.CharField(max_length=50, default=DEFAULT_VALUE)
    market_cap = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                     null=True)
    pe = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True)
    price = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    sector = models.CharField(max_length=50, default=DEFAULT_VALUE)
    stock_exchange = models.CharField(max_length=100, default=DEFAULT_VALUE)
    symbol = models.CharField(max_length=100)

    class Meta:
        """
        Model meta class
        """
        constraints = [
            models.CheckConstraint(check=models.Q(price__gt=0), name='ticker_price_non_negative'),
            models.UniqueConstraint(fields=['stock_exchange', 'symbol'], name='unique_stock_ex_ticker_combination')
        ]
        indexes = [
            models.Index(fields=['company_name', ]),
            models.Index(fields=['country', ]),
            models.Index(fields=['industry', ]),
            models.Index(fields=['sector', ]),
            models.Index(fields=['symbol', ]),
        ]

    def __str__(self):
        return f"{self.symbol}"

    def net_income_statements(self, start_date):
        """
        Returns net income ticker statements
        """
        return self.ticker_statements \
            .filter(name=Statements.net_income,
                    fiscal_date_ending__gte=start_date) \
            .order_by('-fiscal_date_ending')

    def get_debt_statements(self, statement, value_alias):
        """
        Returns ticker statements related to calculating debt to equity and assets to equity
        """
        return Query() \
            .from_table(TickerStatement, [TickerStatement.fiscal_date_ending.field.name,
                                          {value_alias: TickerStatement.value.field.name}]) \
            .where(ticker_id=self.id, name=statement) \
            .group_by(TickerStatement.fiscal_date_ending.field.name) \
            .group_by(TickerStatement.value.field.name) \
            .order_by(TickerStatement.fiscal_date_ending.field.name, desc=True)

    def get_returns_statements(self, statement):
        """
        Returns ticker statements related to calculating ROA and ROE
        """
        quarter = 4
        return self.ticker_statements \
                   .filter(name=statement) \
                   .order_by(f'-{TickerStatement.fiscal_date_ending.field.name}')[:quarter]


class Statements(models.TextChoices):
    """
    Supported statements
    """
    capital_lease_obligations = 'capital_lease_obligations'
    net_income = 'net_income'
    outstanding_shares = 'outstanding_shares'
    price = 'price'
    short_term_debt = 'short_term_debt'
    total_assets = 'total_assets'
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

    class Meta:
        """
        Meta
        """
        unique_together = ['fiscal_date_ending', 'name', 'ticker_id']
