"""
Portfolio Tests
"""
from fin.models.index.index import Index, REASONABLE_LOT_PRICE
from fin.models.portfolio import Portfolio, PortfolioTickers
from fin.models.ticker import Ticker
from fin.tests.base import BaseTestCase
from fin.views import AdjustMixin


class PortfolioTests(BaseTestCase):
    """
    Tests for Portfolio class and related functionality
    """
    fixtures = ['fin/tests/fixtures/ticker.json',
                'fin/tests/fixtures/portfolio.json',
                'fin/tests/fixtures/index.json']

    def test_portfolio_index_queries_diff(self):
        """
        Test function that subtract existed portfolio from index
        """
        expected_result = [
            PortfolioTickers(ticker=Ticker.objects.get(symbol='AAPL'), amount=10),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='TSLA'), amount=1),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='PYPL'), amount=1),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='INTC'), amount=4)
        ]

        portfolio = Portfolio.objects.first()
        index = Index.objects.first()

        portfolio_query = PortfolioTickers.objects.filter(portfolio=portfolio)
        adjusted_index, _ = index.adjust(portfolio.total_tickers + REASONABLE_LOT_PRICE * 2,
                                         AdjustMixin.default_adjust_options, REASONABLE_LOT_PRICE)
        tickers_diff = Portfolio.portfolio_index_queries_diff(adjusted_index, portfolio_query)

        for i in range(0, 3):
            self.assertEqual(expected_result[i].ticker.symbol, tickers_diff[i].get('symbol'))
            self.assertEqual(expected_result[i].amount, tickers_diff[i].get('amount'))
