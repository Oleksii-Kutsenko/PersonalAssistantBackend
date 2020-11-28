"""
Portfolio Tests
"""

from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_406_NOT_ACCEPTABLE, HTTP_202_ACCEPTED, HTTP_200_OK

from fin.models.index.index import Index
from fin.models.portfolio import Portfolio, PortfolioTickers
from fin.models.ticker import Ticker
from fin.models.utils import UpdatingStatus
from fin.tests.base import BaseTestCase
from fin.views import AdjustMixin
from users.models import User


class PortfolioTests(BaseTestCase):
    """
    Tests for Portfolio class and related functionality
    """
    fixtures = ['fin/tests/fixtures/ticker.json',
                'fin/tests/fixtures/portfolio.json',
                'fin/tests/fixtures/index.json']

    def setUp(self) -> None:
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)

    def test_metadata_of_the_portfolio(self):
        """
        Check that portfolio metadata contains the expected fields
        """
        url = reverse('portfolios-list')

        response = self.client.options(url)
        json_data = response.json()

        self.assertIn('pub_', json_data['actions']['POST']['query_params'].keys())
        self.assertIn('sec_', json_data['actions']['POST']['query_params'].keys())

    def test_portfolio_index_queries_diff(self):
        """
        Test function that subtract existed portfolio from index
        """
        expected_result = [
            PortfolioTickers(ticker=Ticker.objects.get(symbol='AAPL'), amount=7),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='TSLA'), amount=1),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='PYPL'), amount=1),
            PortfolioTickers(ticker=Ticker.objects.get(symbol='INTC'), amount=2)
        ]
        step = 200

        portfolio = Portfolio.objects.first()
        index = Index.objects.first()

        portfolio_query = PortfolioTickers.objects.filter(portfolio=portfolio)
        adjusted_index, _ = index.adjust(portfolio.total_tickers + step * 2,
                                         AdjustMixin.default_adjust_options, step)
        tickers_diff = Portfolio.portfolio_index_queries_diff(adjusted_index, portfolio_query)

        for i in range(0, 4):
            self.assertEqual(expected_result[i].ticker.symbol, tickers_diff[i].get('symbol'))
            self.assertEqual(expected_result[i].amount, tickers_diff[i].get('amount'))

    def test_update_portfolio_tickers(self):
        """
        Tests that endpoint returns desirable responses
        """
        portfolio = Portfolio.objects.first()
        update_portfolio_tickers_url = reverse('portfolios-update-tickers',
                                               kwargs={'pk': portfolio.id})

        response = self.client.put(update_portfolio_tickers_url)
        self.assertEqual(response.status_code, HTTP_202_ACCEPTED)

        portfolio.status = UpdatingStatus.updating
        portfolio.save()

        response = self.client.put(update_portfolio_tickers_url)
        self.assertEqual(response.status_code, HTTP_406_NOT_ACCEPTABLE)

        portfolio.status = UpdatingStatus.successfully_updated
        portfolio.save()
        for ticker in portfolio.tickers.all():
            ticker.updated = timezone.now()
            ticker.save()

        response = self.client.put(update_portfolio_tickers_url)
        self.assertEqual(response.status_code, HTTP_200_OK)
