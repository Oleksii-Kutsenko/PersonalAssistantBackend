"""
Tests for AV parsers
"""

from fin.external_api.alpha_vantage.parsers import parse_time_series_monthly
from fin.models.portfolio import Portfolio, PortfolioTicker
from fin.models.ticker import Ticker, TickerStatement
from fin.tests.base import BaseTestCase
from users.models import User


class AVParsersTests(BaseTestCase):
    """
    Tests for parsers Alpha Vantage responses
    """

    fixtures = ["fin/tests/fixtures/ticker.json"]

    def setUp(self) -> None:
        self.user = User.objects.create(
            username="test_user", email="test_user@gmail.com"
        )
        self.login(self.user)

    def test_parse_time_series_monthly(self):
        """
        Tests that parse_time_series_monthly returns correct TickerStatements and they displays
        inside TickerSerializer
        """
        ticker = Ticker.objects.get(symbol="AAPL")

        portfolio = Portfolio.objects.create(name="test_portfolio", user=self.user)
        portfolio.save()

        portfolio_ticker = PortfolioTicker(portfolio=portfolio, ticker=ticker, amount=1)
        portfolio_ticker.save()

        ticker_time_series = {
            "Meta Data": {
                "1. Information": "Monthly Adjusted Prices and Volumes",
                "2. Symbol": "AAPL",
                "3. Last Refreshed": "2020-08-19",
                "4. Time Zone": "US/Eastern",
            },
            "Monthly Adjusted Time Series": {
                "2020-08-19": {
                    "1. open": "432.8000",
                    "2. high": "468.6500",
                    "3. low": "431.5700",
                    "4. close": "462.8300",
                    "5. adjusted close": "462.8300",
                    "6. volume": "578551329",
                    "7. dividend amount": "0.8200",
                },
                "2020-07-31": {
                    "1. open": "365.1200",
                    "2. high": "425.6600",
                    "3. low": "356.5800",
                    "4. close": "425.0400",
                    "5. adjusted close": "424.2573",
                    "6. volume": "755087646",
                    "7. dividend amount": "0.0000",
                },
                "2020-06-30": {
                    "1. open": "317.7500",
                    "2. high": "372.3800",
                    "3. low": "317.2100",
                    "4. close": "364.8000",
                    "5. adjusted close": "364.1282",
                    "6. volume": "810739319",
                    "7. dividend amount": "0.0000",
                },
                "2000-01-01": {
                    "1. open": "317.7500",
                    "2. high": "372.3800",
                    "3. low": "317.2100",
                    "4. close": "364.8000",
                    "5. adjusted close": "None",
                    "6. volume": "810739319",
                    "7. dividend amount": "0.0000",
                },
            },
        }
        expected_length = len(ticker_time_series["Monthly Adjusted Time Series"].keys())
        tickers_statements = parse_time_series_monthly(ticker, ticker_time_series)
        TickerStatement.objects.bulk_create(tickers_statements)

        tickers_statements = ticker.ticker_statements.order_by("-fiscal_date_ending")
        assert len(tickers_statements) == expected_length
