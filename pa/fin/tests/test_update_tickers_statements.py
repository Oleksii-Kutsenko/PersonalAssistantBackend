"""
Tests for main functionality of update_tickers_statements_task
"""
from fin.models.ticker import Ticker, Statements
from fin.tasks.update_tickers_statements import update_tickers_statements
from fin.tests.base import BaseTestCase


class UpdateTickersStatementsTests(BaseTestCase):
    """
    Tests for main functionality of celery task
    """
    fixtures = ['fin/tests/fixtures/empty_ticker.json']

    def test_update_tickers_statements(self):
        """
        Check that ticker will be updated
        """
        test_ticker = 'AAPL'
        query = Ticker.objects.filter(symbol=test_ticker)
        ticker = query.first()
        old_ticker_price = ticker.price

        update_tickers_statements(query)
        self.assertNotEqual(Ticker.industry, Ticker.DEFAULT_VALUE)

        net_income = ticker.ticker_statements.filter(name=Statements.net_income.value).first()
        self.assertNotEqual(net_income, None)

        total_assets = ticker.ticker_statements.filter(name=Statements.total_assets.value).first()
        self.assertNotEqual(total_assets, None)

        ticker_price = ticker.ticker_statements \
            .filter(name='price') \
            .order_by('-fiscal_date_ending').first()
        self.assertNotEqual(ticker_price, old_ticker_price)
