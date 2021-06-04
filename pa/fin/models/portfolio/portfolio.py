"""
Portfolio model and related models
"""
from decimal import Decimal

from django.db import models
from django.db.models import ForeignKey, CASCADE, ManyToManyField, IntegerField, CharField, \
    DecimalField, F, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from fin.external_api.exante import get_jwt, get_account_summary
from fin.models.index import Index
from fin.models.stock_exchange import StockExchange
from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus
from fin.serializers.ticker import TickerSerializer
from users.models import User


class PortfolioTicker(TimeStampMixin):
    """
    Associated table for M2M relation between Portfolio model and Ticker model
    """
    portfolio = ForeignKey('Portfolio', on_delete=CASCADE, related_name='portfolio')
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


class Portfolio(TimeStampMixin):
    """
    Class that represents the portfolio
    """
    exante_account_id = CharField(max_length=50)
    name = CharField(max_length=100)
    status = models.IntegerField(choices=UpdatingStatus.choices,
                                 default=UpdatingStatus.successfully_updated)
    tickers = ManyToManyField(Ticker, through='fin.PortfolioTicker')
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

        proper_portfolio_tickers = PortfolioTicker.objects \
            .filter(portfolio=self) \
            .filter(ticker__symbol__in=index.tickers.values_list('symbol', flat=True))
        proper_portfolio_tickers_sum = proper_portfolio_tickers.annotate(cost=cost) \
                                           .aggregate(Sum('cost')).get('cost__sum') or 0

        adjusted_index_tickers = index.adjust(float(proper_portfolio_tickers_sum) + money, options)
        ticker_diff = self.ticker_difference(adjusted_index_tickers, proper_portfolio_tickers)
        packed_ticker_diff = self.pack_tickers_difference(money, ticker_diff)
        return packed_ticker_diff

    def import_from_exante(self):
        """
        Import portfolio from the EXANTE
        """
        stock_exchanges_mapper = StockExchange.get_stock_exchanges_mapper()

        jwt = get_jwt()
        account_summary = get_account_summary(self.exante_account_id, jwt)

        accounts = []
        currencies = account_summary.pop('currencies')
        for account in currencies:
            accounts.append(Account(name=account.get('code'), currency=Account.Currency(account.get('code')),
                                    portfolio=self, value=Decimal(account.get('value'))))
        self.accounts.all().delete()
        Account.objects.bulk_create(accounts)

        portfolio_tickers = []
        positions = account_summary.pop('positions')
        for position in positions:
            symbol, stock_exchange = position.get('symbolId').split('.')
            if position.get('currency') != Account.Currency.USD:
                price = Decimal(position.get('convertedValue')) / Decimal(position.get('quantity'))
            else:
                price = Decimal(position.get('price'))

            ticker = None
            ticker_qs = Ticker.objects.filter(symbol=symbol)
            if ticker_qs.count() == 1:
                ticker = ticker_qs.first()
                ticker.price = price
                ticker.save()
            elif ticker_qs.count() > 1:
                ticker_qs = ticker_qs.filter(stock_exchange_id=stock_exchanges_mapper[stock_exchange])
                if ticker_qs.count() == 1:
                    ticker = ticker_qs.first()
                    ticker.price = price
                    ticker.save()
                elif ticker_qs.count() > 1:
                    raise NotImplementedError('Unexpected situation')

            if ticker is None:
                ticker = Ticker.objects.create(symbol=symbol, stock_exchange_id=stock_exchanges_mapper[stock_exchange],
                                               price=price)

            portfolio_tickers.append(PortfolioTicker(portfolio=self, ticker=ticker, amount=position.get('quantity')))

        PortfolioTicker.objects.filter(portfolio=self).delete()
        PortfolioTicker.objects.bulk_create(portfolio_tickers)

    @staticmethod
    def pack_tickers_difference(money, ticker_diff):
        """
        Tries to pack the tickers difference so that the tickers sum is less than the money
        parameter
        """
        result = []
        for ticker in ticker_diff:
            amount = money // float(ticker['price'])
            if amount == 0:
                continue
            if amount < ticker['amount']:
                ticker['amount'] = amount
            ticker['cost'] = ticker['amount'] * float(ticker['price'])
            money -= ticker['cost']
            result.append(ticker)
        return result

    @staticmethod
    def ticker_difference(adjusted_index_tickers, portfolio_tickers):
        """
        Excludes tickers already present in the portfolio from the adjusted index tickers
        """
        result = []
        for _, adjusted_ticker in adjusted_index_tickers.iterrows():
            ticker_id = adjusted_ticker['ticker__id']
            portfolio_ticker = portfolio_tickers.filter(ticker__id=ticker_id).first()

            if portfolio_ticker:
                ticker = portfolio_ticker.ticker
                amount = adjusted_ticker['amount'] - portfolio_ticker.amount
            else:
                ticker = Ticker.objects.get(id=ticker_id)
                amount = adjusted_ticker['amount']

            if amount > 0:
                result.append({
                    **TickerSerializer(ticker).data,
                    'amount': amount,
                    'cost': float(ticker.price) * amount,
                    'weight': adjusted_ticker['weight']
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
        query = PortfolioTicker.objects.filter(portfolio=self).annotate(cost=cost)
        tickers_sum = query.aggregate(Sum('cost')).get('cost__sum')
        if tickers_sum:
            return Decimal(tickers_sum)
        return 0


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        """
        Available currencies for account
        """
        CAD = 'CAD', _('Canadian Dollar')
        EUR = 'EUR', _("Euro")
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")

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
