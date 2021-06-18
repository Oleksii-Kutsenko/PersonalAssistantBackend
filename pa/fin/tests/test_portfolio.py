"""
Portfolio Tests
"""
import os

from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_406_NOT_ACCEPTABLE, HTTP_202_ACCEPTED, HTTP_200_OK

from fin.mixins import AdjustMixin
from fin.models.index.index import Index
from fin.models.portfolio import Portfolio, PortfolioTicker
from fin.models.utils import UpdatingStatus
from fin.tests.base import BaseTestCase
from fin.tests.factories.portfolio import PortfolioFactory
from fin.tests.factories.portfolio_policy import PortfolioPolicyFactory
from users.models import User


class PortfolioTests(BaseTestCase):
    """
    Tests for Portfolio class and related functionality
    """
    fixtures = [
        'fin/tests/fixtures/index.json',
        'fin/tests/fixtures/index_ticker.json',
        'fin/tests/fixtures/portfolio.json',
        'fin/tests/fixtures/portfolio_ticker.json',
        'fin/tests/fixtures/sources.json',
        'fin/tests/fixtures/stock_exchanges.json',
        'fin/tests/fixtures/stock_exchanges_aliases.json',
        'fin/tests/fixtures/tickers.json',
        'fin/tests/fixtures/users.json'
    ]

    def setUp(self) -> None:
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)

        portfolio = Portfolio.objects.first()
        portfolio.user = self.user
        portfolio.save()

    def test_portfolio_adjusting(self):
        """
        Tests that portfolio adjusting works properly
        """
        expected_tickers = {
            'AAPL': 1,
            'BAC': 1,
            'GE': 1
        }
        portfolio_policy = PortfolioPolicyFactory()
        portfolio = portfolio_policy.portfolio
        index = Index.objects.get(source__url='https://www.ishares.com/us/products/239724/'
                                              'ishares-core-sp-total-us-stock-market-etf/1467271812596.ajax')
        url = reverse('portfolios-adjust', kwargs={'pk': portfolio.id, 'index_id': index.id})

        response = self.client.get(url, {'money': 200})

        for ticker in response.data['tickers']:
            self.assertEqual(expected_tickers[ticker['symbol']], ticker['amount'])

    def test_portfolio_displayable_status(self):
        """
        Tests that portfolio statuses displayed properly
        """
        portfolio = Portfolio.objects.first()
        url = reverse('portfolios-detail', kwargs={'pk': portfolio.id})

        for status in UpdatingStatus:
            portfolio.status = status.value
            portfolio.save()
            response = self.client.get(url)
            self.assertEqual(response.data['status'], status.label)

    def test_portfolio_importing(self):
        """
        Test portfolio importing from Exante Api
        """
        portfolio = PortfolioFactory()
        portfolio.exante_account_id = os.environ.get('ACCOUNT_ID')
        portfolio.save()

        portfolio.import_from_exante()
        self.assertGreaterEqual(portfolio.accounts.count(), 1)
        self.assertGreaterEqual(portfolio.tickers.count(), 1)

    def test_portfolio_index_queries_diff(self):
        """
        Test function that subtract existed portfolio from index
        """
        expected_result = [
            (31818, 2),
            (31832, 1),
            (31837, 1),
            (31838, 1),
            (31846, 1),
            (31847, 1),
            (31885, 1)
        ]
        step = 200

        portfolio = Portfolio.objects.first()
        index = Index.objects.first()

        portfolio_query = PortfolioTicker.objects.filter(portfolio=portfolio)
        adjusted_index = index.adjust(float(portfolio.total_tickers), step, AdjustMixin.default_adjust_options)
        tickers_diff = Portfolio.tickers_difference(adjusted_index, portfolio_query)

        for i in range(0, 4):
            self.assertEqual(expected_result[i][0], tickers_diff.iloc[i].id)
            self.assertEqual(expected_result[i][1], tickers_diff.iloc[i].amount)

    def test_portfolio_breakdowns_calculation(self):
        """
        Tests that the breakdowns in the Portfolio model calculate properly
        """
        portfolio = Portfolio.objects.first()
        url = reverse('portfolios-detail', kwargs={'pk': portfolio.id})
        expected_industries = {}
        expected_sectors = {}
        portfolio_tickers = PortfolioTicker.objects.filter(portfolio=portfolio)

        for portfolio_ticker in portfolio_tickers:
            ticker_cost = portfolio_ticker.ticker.price * portfolio_ticker.amount

            if expected_sectors.get(portfolio_ticker.ticker.sector):
                expected_sectors[portfolio_ticker.ticker.sector] += ticker_cost
            else:
                expected_sectors[portfolio_ticker.ticker.sector] = ticker_cost

            if expected_industries.get(portfolio_ticker.ticker.industry):
                expected_industries[portfolio_ticker.ticker.industry] += ticker_cost
            else:
                expected_industries[portfolio_ticker.ticker.industry] = ticker_cost

        response = self.client.get(url)

        given_sectors = {}
        for sector in response.data['sectors_breakdown']:
            given_sectors[sector['ticker__sector']] = sector['sum_cost']
        given_industries = {}
        for industry in response.data['industries_breakdown']:
            given_industries[industry['ticker__industry']] = industry['sum_cost']

        self.assertEqual(given_sectors, expected_sectors)
        self.assertEqual(given_industries, expected_industries)

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
