from django.db import models
from django.db.models import ForeignKey, CASCADE, ManyToManyField, IntegerField, CharField, DecimalField, F, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from fin.models.index import Ticker, Index
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES
from users.models import User


class Portfolio(TimeStampMixin):
    name = CharField(max_length=100)
    tickers = ManyToManyField(Ticker, through='PortfolioTickers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['user', ]),
        ]

    def adjust(self, index_id, money, options):
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)
        index = Index.objects.get(pk=index_id)

        proper_portfolio_tickers = PortfolioTickers.objects \
            .filter(portfolio=self) \
            .filter(ticker__symbol__in=index.tickers.values_list('symbol', flat=True))

        proper_portfolio_tickers_sum = proper_portfolio_tickers.annotate(cost=cost).aggregate(Sum('cost'))
        proper_portfolio_tickers_sum = proper_portfolio_tickers_sum.get('cost__sum') or 0

        adjusted_index_query, summary_cost = index.adjust(proper_portfolio_tickers_sum + money, options, step=money)
        return adjusted_index_query, summary_cost


class PortfolioTickers(TimeStampMixin):
    portfolio = ForeignKey(Portfolio, on_delete=CASCADE, related_name='portfolio')
    ticker = ForeignKey(Ticker, on_delete=CASCADE, related_name='portfolio_ticker')
    amount = IntegerField()

    class Meta:
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
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['currency', ]),
        ]
