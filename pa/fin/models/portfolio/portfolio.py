"""
Portfolio model and related models
"""
from decimal import Decimal

from django.db import models
from django.db.models import ForeignKey, CASCADE, ManyToManyField, IntegerField, CharField, \
    DecimalField, F, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from fin.models.index import Index
from fin.models.index.index import REASONABLE_LOT_PRICE
from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus
from fin.serializers.ticker import AdjustedTickerSerializer
from users.models import User


class Portfolio(TimeStampMixin):
    """
    Class that represents the portfolio
    """
    name = CharField(max_length=100)
    status = models.IntegerField(choices=UpdatingStatus.choices,
                                 default=UpdatingStatus.successfully_updated)
    tickers = ManyToManyField(Ticker, through='PortfolioTickers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        """
        Model meta class
        """
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['user', ]),
        ]

    def adjust(self, index_id, money, options):
        """
        The function that tries to make the portfolio more similar to some Index
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)
        index = Index.objects.get(pk=index_id)

        proper_portfolio_tickers = PortfolioTickers.objects \
            .filter(portfolio=self) \
            .filter(ticker__symbol__in=index.tickers.values_list('symbol', flat=True))

        proper_portfolio_tickers_sum = proper_portfolio_tickers \
                                           .annotate(cost=cost) \
                                           .aggregate(Sum('cost')) \
                                           .get('cost__sum') or 0

        adjusted_index, _ = index.adjust(proper_portfolio_tickers_sum + money * 2, options, money)
        ticker_diff = self.portfolio_index_queries_diff(adjusted_index, proper_portfolio_tickers)
        packed_ticker_diff = self.pack_ticker_diff(ticker_diff, money)
        return packed_ticker_diff

    @staticmethod
    def pack_ticker_diff(ticker_diff, money):
        """
        Tries to pack the tickers difference so that the tickers sum is less than the money
        parameter
        """
        result = []
        for ticker in ticker_diff:
            amount = money // Decimal(ticker['price'])
            if amount == 0 or amount * Decimal(ticker['price']) < REASONABLE_LOT_PRICE:
                continue
            if amount < ticker['amount']:
                ticker['amount'] = amount
            ticker['cost'] = Decimal(ticker['price']) * Decimal(ticker['amount'])
            money -= ticker['cost']
            result.append(ticker)
        return result

    @staticmethod
    def portfolio_index_queries_diff(index_query, portfolio_query):
        """
        Return query that exclude tickers from portfolio
        """
        result = []
        for adjusted_ticker in index_query:
            matched_portfolio_ticker = portfolio_query \
                .filter(ticker__symbol=adjusted_ticker.ticker.symbol) \
                .first()

            if matched_portfolio_ticker:
                amount_diff = adjusted_ticker.amount - matched_portfolio_ticker.amount
                cost = adjusted_ticker.ticker.price * amount_diff
                if cost >= REASONABLE_LOT_PRICE:
                    adjusted_ticker.amount -= matched_portfolio_ticker.amount
                    result.append({
                        **AdjustedTickerSerializer(adjusted_ticker).data,
                    })
            else:
                result.append({
                    **AdjustedTickerSerializer(adjusted_ticker).data,
                })
        return result

    @property
    def total(self):
        """
        Total sum of the portfolio tickers and accounts
        """
        return self.total_accounts + self.total_tickers

    @property
    def total_accounts(self):
        """
        Total sum of the portfolio accounts cost
        """
        accounts_sum = Account.objects.filter(portfolio=self) \
            .aggregate(Sum('value')).get('value__sum')
        return accounts_sum or 0

    @property
    def total_tickers(self):
        """
        Total sum of the portfolio tickers cost
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)
        query = PortfolioTickers.objects.filter(portfolio=self).annotate(cost=cost)
        tickers_sum = query.aggregate(Sum('cost')).get('cost__sum')
        return tickers_sum or 0


class PortfolioTickers(TimeStampMixin):
    """
    Associated table for M2M relation between Portfolio model and Ticker model
    """
    portfolio = ForeignKey(Portfolio, on_delete=CASCADE, related_name='portfolio')
    ticker = ForeignKey(Ticker, on_delete=CASCADE, related_name='portfolio_ticker')
    amount = IntegerField()

    class Meta:
        """
        Model meta class
        """
        indexes = [
            models.Index(fields=['portfolio', ]),
            models.Index(fields=['ticker', ]),
        ]


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

    class Meta:
        """
        Model meta class
        """
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['currency', ]),
        ]
