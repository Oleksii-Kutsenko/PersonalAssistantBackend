"""
Portfolio model and related models
"""
from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Cast

from fin.models.account import Account
from fin.models.index import Index
from fin.models.portfolio.portfolio_ticker import PortfolioTicker
from fin.models.stock_exchange import StockExchangeAlias
from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus
from fin.serializers.ticker import TickerSerializer
from users.models import User


class Portfolio(TimeStampMixin):
    """
    Class that represents the portfolio
    """

    name = models.CharField(max_length=100)
    status = models.IntegerField(
        choices=UpdatingStatus.choices, default=UpdatingStatus.successfully_updated
    )
    tickers = models.ManyToManyField(Ticker, through="fin.PortfolioTicker")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        """
        Model meta class
        """

        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                ]
            ),
        ]

    def adjust(self, index_id, extra_money, options):
        """
        The function that tries to make the portfolio more similar to some Index
        """
        decimal_field = DecimalField(
            max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES
        )
        cost = Cast(F("amount") * F("ticker__price"), decimal_field)
        index = Index.objects.get(pk=index_id)

        portfolio_tickers = PortfolioTicker.objects.filter(portfolio=self).filter(
            ticker__id__in=index.tickers.values_list("id", flat=True)
        )
        portfolio_tickers_sum = (
            portfolio_tickers.annotate(cost=cost)
            .aggregate(Sum("cost"))
            .get("cost__sum")
            or 0
        )

        tickers_df = index.adjust(float(portfolio_tickers_sum), extra_money, options)
        tickers_diff_df = self.tickers_difference(tickers_df, portfolio_tickers)
        packed_ticker_diff = self.pack_tickers_difference(extra_money, tickers_diff_df)

        tickers_qs = Ticker.objects.filter(id__in=packed_ticker_diff.keys())
        response = TickerSerializer(tickers_qs, many=True).data
        for ticker in response:
            ticker.update(packed_ticker_diff[ticker["id"]])
        return response

    def import_from_exante(self, secret_key):
        """
        Import portfolio from the EXANTE
        """
        jwt = self.exantesettings.get_jwt(secret_key)
        account_summary = self.exantesettings.get_account_summary(jwt)
        exante_portfolio_importer = ExantePortfolioImporter(account_summary, jwt, self)

        accounts = exante_portfolio_importer.get_accounts()
        self.accounts.all().delete()
        Account.objects.bulk_create(accounts)

        portfolio_tickers = exante_portfolio_importer.get_portfolio_tickers()
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

            result[ticker_df_row.id] = {
                "amount": ticker_df_row.amount,
                "cost": ticker_df_row.cost,
            }

            money -= ticker_df_row.cost
            if money < min_price:
                break

        return result

    @staticmethod
    def tickers_difference(tickers_df, portfolio_tickers):
        """
        Excludes tickers already present in the portfolio from the adjusted index tickers
        """
        matched_portfolio_tickers = portfolio_tickers.filter(
            ticker__id__in=tickers_df.id.values
        )
        for matched_ticker in matched_portfolio_tickers:
            condition = tickers_df.id == matched_ticker.ticker.id
            tickers_df.loc[condition, "amount"] -= matched_ticker.amount

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
        accounts_sum = (
            Account.objects.filter(portfolio=self)
            .aggregate(Sum("value"))
            .get("value__sum")
        )
        return accounts_sum or 0

    @property
    def total_tickers(self):
        """
        Total sum of the portfolio tickers cost
        """
        decimal_field = DecimalField(
            max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES
        )
        cost = Cast(F("amount") * F("ticker__price"), decimal_field)
        query = PortfolioTicker.objects.filter(portfolio=self).annotate(cost=cost)
        tickers_sum = query.aggregate(Sum("cost")).get("cost__sum")
        if tickers_sum:
            return Decimal(tickers_sum)
        return 0


class ExantePortfolioImporter:
    """
    Class for importing portfolio from EXANTE API data
    """

    def __init__(self, account_summary, jwt, portfolio):
        self.account_summary = account_summary
        self.jwt = jwt
        self.portfolio = portfolio

    def get_accounts(self):
        """
        Creates Account objects from EXANTE API data
        """
        accounts = []
        currencies = self.account_summary.get("currencies")
        for account in currencies:
            accounts.append(
                Account(
                    currency=Account.Currency(account.get("code")),
                    name=account.get("code"),
                    portfolio=self.portfolio,
                    value=Decimal(account.get("value")),
                )
            )
        return accounts

    def get_portfolio_tickers(self):
        """
        Creates PortfolioTicker objects from EXANTE API data
        """
        portfolio_tickers = []
        positions = self.account_summary.get("positions")
        stock_exchanges_mapper = dict(
            StockExchangeAlias.objects.values_list("alias", "stock_exchange_id")
        )

        for position in positions:
            if not (quantity := Decimal(position.get("quantity"))):  # exante bug
                continue

            symbol, stock_exchange = position.get("symbolId").split(".")
            if position.get("currency") != Account.Currency.USD:
                price = Decimal(position.get("convertedValue")) / quantity
            else:
                price = Decimal(position.get("price"))

            ticker = Ticker.find_by_symbol_and_stock_exchange_id(
                symbol, stock_exchanges_mapper[stock_exchange]
            )

            if ticker is None:
                ticker = Ticker.objects.create(
                    stock_exchange_id=stock_exchanges_mapper[stock_exchange],
                    symbol=symbol,
                    price=price,
                )

            portfolio_tickers.append(
                PortfolioTicker(
                    portfolio=self.portfolio, ticker=ticker, amount=quantity
                )
            )
        return portfolio_tickers
