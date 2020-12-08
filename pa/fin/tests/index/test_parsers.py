"""
Tests for Index parsers
"""
from random import choice

from fin.models.index import Index
from fin.models.index.parsers import SlickChartsParser
from fin.tests.base import BaseTestCase


class IndexParsersTests(BaseTestCase):
    """
    Tests for Index parsers
    """
    def test_slick_charts_parser(self):
        """
        Tests the parsing for SlickCharts data source
        """
        data_sources = [url for url, parser in Index.url_parsers.items()
                        if isinstance(parser, SlickChartsParser)]
        parser = SlickChartsParser(choice(data_sources))
        json = parser.parse()
        for index_ticker in json:
            self.assertIn('ticker', index_ticker)
            self.assertIn('ticker_weight', index_ticker)
            self.assertIn('symbol', index_ticker['ticker'])
            self.assertIn('price', index_ticker['ticker'])
