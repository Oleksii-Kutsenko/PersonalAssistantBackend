"""
Portfolio model and related models
"""
from decimal import Decimal

from django.db import models
from django.db.models import ForeignKey, CASCADE, ManyToManyField, IntegerField, CharField, \
    DecimalField, F, Sum
from django.db.models.functions import Cast

from fin.external_api.exante import get_jwt, get_account_summary
from fin.models.account import Account
from fin.models.index import Index
from fin.models.stock_exchange import StockExchangeAlias
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
        constraints = [
            models.UniqueConstraint(fields=['portfolio_id', 'ticker_id'], name='portfolio_id_ticker_id_unique')
        ]
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

    def adjust(self, index_id, extra_money, options):
        """
        The function that tries to make the portfolio more similar to some Index
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)
        index = Index.objects.get(pk=index_id)

        portfolio_tickers = PortfolioTicker.objects \
            .filter(portfolio=self) \
            .filter(ticker__symbol__in=index.tickers.values_list('symbol', flat=True))
        portfolio_tickers_sum = portfolio_tickers.annotate(cost=cost).aggregate(Sum('cost')).get('cost__sum') or 0

        tickers_df = index.adjust(float(portfolio_tickers_sum), extra_money, options)
        tickers_diff_df = self.tickers_difference(tickers_df, portfolio_tickers)
        packed_ticker_diff = self.pack_tickers_difference(extra_money, tickers_diff_df)

        tickers_qs = Ticker.objects.filter(id__in=packed_ticker_diff.keys())
        response = TickerSerializer(tickers_qs, many=True).data
        for ticker in response:
            ticker.update(packed_ticker_diff[ticker['id']])
        return response

    def import_from_exante(self):
        """
        Import portfolio from the EXANTE
        """
        stock_exchanges_mapper = dict(StockExchangeAlias.objects.values_list('alias', 'stock_exchange_id', ))

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

            ticker = Ticker.find_by_symbol_and_stock_exchange_id(symbol, stock_exchanges_mapper[stock_exchange])

            if ticker is None:
                ticker = Ticker.objects.create(symbol=symbol, stock_exchange_id=stock_exchanges_mapper[stock_exchange],
                                               price=price)

            portfolio_tickers.append(PortfolioTicker(portfolio=self, ticker=ticker, amount=position.get('quantity')))

        PortfolioTicker.objects.filter(portfolio=self).delete()
        PortfolioTicker.objects.bulk_create(portfolio_tickers)

    @staticmethod
    def pack_tickers_difference(money, tickers_diff_df):
        """
        Tries to pack the tickers difference so that the tickers sum is less than the money
        parameter
        """
        result = {}
        min_price = tickers_diff_df.price.min()
        for _, ticker_df_row in tickers_diff_df.iterrows():
            max_amount = money // float(ticker_df_row.price)

            if max_amount == 0:
                continue
            if max_amount < ticker_df_row.amount:
                ticker_df_row.amount = max_amount
            ticker_df_row.cost = round(ticker_df_row.amount * ticker_df_row.price, 2)

            result[ticker_df_row.id] = {'amount': ticker_df_row.amount,
                                        'cost': ticker_df_row.cost}

            money -= ticker_df_row.cost
            if money < min_price:
                break

        return result

    @staticmethod
    def tickers_difference(tickers_df, portfolio_tickers):
        """
        Excludes tickers already present in the portfolio from the adjusted index tickers
        """
        matched_portfolio_tickers = portfolio_tickers.filter(ticker__id__in=tickers_df.id.values)
        for matched_ticker in matched_portfolio_tickers:
            condition = tickers_df.id == matched_ticker.ticker.id
            tickers_df.loc[condition, 'amount'] -= matched_ticker.amount

        tickers_df = tickers_df[tickers_df.amount > 0]
        return tickers_df

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
