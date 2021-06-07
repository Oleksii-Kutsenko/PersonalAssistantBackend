"""
Tests for indexes parsers
"""
from decimal import Decimal

from fin.models.index.parsers import AmplifyParser, Source
from fin.tests.base import BaseTestCase


class ParsersTests(BaseTestCase):
    """
    Index parsers test cases
    """
    fixtures = [
        'fin/migrations/fixtures/stock_exchanges.json'
    ]

    def test_amplify_parser(self):
        """
        Tests that AmplifyParser works properly
        """
        parser = AmplifyParser(Source.IBUY)
        parsed_index_tickers = parser.parse()

        coefficient_sum = 0
        for parsed_index_ticker in parsed_index_tickers:
            self.assertGreater(parsed_index_ticker.ticker.price, Decimal('0'))
            coefficient_sum += parsed_index_ticker.weight
        self.assertAlmostEqual(coefficient_sum / 100, 1, places=2)
