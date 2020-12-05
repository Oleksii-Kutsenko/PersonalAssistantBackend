"""
Ticker Tests
"""
from fin.models.ticker import Ticker
from fin.serializers.ticker import TickerSerializer
from fin.tests.base import BaseTestCase


class TickersTests(BaseTestCase):
    """
    Tests for Ticker class and related functionality
    """
    fixtures = ['fin/tests/fixtures/empty_ticker.json',
                'fin/tests/fixtures/aapl_ticker_statements.json']

    def test_annual_earnings_growth_calculation(self):
        """
        Tests that annual earnings growth calculates correcly
        """
        expected_annual_earnings_growth = 1.041

        ticker = Ticker.objects.first()
        serializer = TickerSerializer()
        annual_earnings_growth = serializer.get_annual_earnings_growth(ticker)

        self.assertAlmostEqual(annual_earnings_growth, expected_annual_earnings_growth, places=2)
