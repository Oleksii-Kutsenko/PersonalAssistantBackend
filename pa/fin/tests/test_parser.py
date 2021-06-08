"""
Tests for indexes parsers
"""
from decimal import Decimal

from fin.models.index import Source
from fin.models.index.parsers import AmplifyParser
from fin.tests.base import BaseTestCase


class ParsersTests(BaseTestCase):
    """
    Index parsers test cases
    """
    fixtures = [
        'fin/tests/fixtures/sources.json',
        'fin/tests/fixtures/stock_exchanges.json',
        'fin/tests/fixtures/stock_exchanges_aliases.json'
    ]

    def test_amplify_parser(self):
        """
        Tests that AmplifyParser works properly
        """
        source = Source.objects.filter(parser_name=AmplifyParser.__name__).first()
        parser = AmplifyParser(source)
        parsed_index_tickers = parser.parse()

        coefficient_sum = 0
        for parsed_index_ticker in parsed_index_tickers:
            self.assertGreater(parsed_index_ticker.ticker.price, Decimal('0'))
            coefficient_sum += parsed_index_ticker.weight
        self.assertAlmostEqual(coefficient_sum / 100, 1, places=2)
