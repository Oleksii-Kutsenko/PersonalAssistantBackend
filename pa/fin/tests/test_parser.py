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
        parsed_json = parser.parse()

        coefficient_sum = 0
        for ticker_info in parsed_json:
            self.assertGreater(ticker_info['ticker']['price'], Decimal('0'))
            coefficient_sum += ticker_info['ticker_weight']
        self.assertAlmostEqual(coefficient_sum / 100, 1, places=2)
