"""
Tests for AV
"""
import time
from datetime import datetime

from fin.external_api.alpha_vantage import AlphaVantage, AVFunctions
from fin.tests.base import BaseTestCase


class AVTests(BaseTestCase):
    """
    Tests for Alpha Vantage API
    """
    def test_av_wait(self):
        """
        Tests an awaiting of Alpha Vantage client
        """
        time.sleep(AlphaVantage.STEP)
        test_symbol = 'AAPL'

        av_api = AlphaVantage()
        for _ in range(5):
            av_api.call(AVFunctions.overview.value, test_symbol)

        start_time = datetime.now()
        av_api.call(AVFunctions.overview.value, test_symbol)
        end_time = datetime.now()

        difference = end_time - start_time
        self.assertGreaterEqual(difference.seconds, AlphaVantage.STEP)
