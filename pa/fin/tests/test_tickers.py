"""
Ticker Tests
"""
from datetime import date

from dateutil.relativedelta import relativedelta

from fin.models.ticker import Ticker, Statements
from fin.serializers.ticker import TickerSerializer
from fin.tests.base import BaseTestCase
from fin.tests.factories.ticker_statement import TickerStatementFactory


class TickersTests(BaseTestCase):
    """
    Tests for Ticker class and related functionality
    """
    fixtures = ['fin/tests/fixtures/empty_ticker.json',
                'fin/tests/fixtures/aapl_ticker_statements.json']

    def test_annual_earnings_growth_calculation(self):
        """
        Tests that annual earnings growth calculates correctly
        """
        expected_annual_earnings_growth = 5.75

        ticker = Ticker.objects.first()
        serializer = TickerSerializer()
        annual_earnings_growth = serializer.get_annual_earnings_growth(ticker)

        self.assertAlmostEqual(annual_earnings_growth, expected_annual_earnings_growth, places=2)

    def test_shares_dilution_calculation(self):
        """
        Tests that shares dilution calculates correctly
        """
        expected_dilution_rate = 100

        ticker = Ticker.objects.first()
        TickerStatementFactory(name=Statements.outstanding_shares,
                               fiscal_date_ending=date.today(),
                               value=4,
                               ticker=ticker).save()
        TickerStatementFactory(name=Statements.outstanding_shares,
                               fiscal_date_ending=date.today() - relativedelta(years=2, days=1),
                               value=1,
                               ticker=ticker).save()
        last_year = date.today() - relativedelta(years=1)
        last_year_shares_amount = TickerStatementFactory(name=Statements.outstanding_shares,
                                                         fiscal_date_ending=last_year,
                                                         value=2,
                                                         ticker=ticker)
        last_year_shares_amount.save()

        serializer = TickerSerializer()
        dilution_rate = serializer.get_shares_dilution(ticker)
        self.assertEqual(dilution_rate, expected_dilution_rate)

        last_year_shares_amount.delete()

        dilution_rate = serializer.get_shares_dilution(ticker)
        self.assertEqual(dilution_rate, None)

    def test_roe_roa_calculation(self):
        """
        Tests that ROA and ROE ratios calculates correctly
        """
        expected_roa = 18
        expected_roe = 88
        ticker = Ticker.objects.first()
        serializer = TickerSerializer()

        ratios = serializer.get_returns_ratios(ticker)
        self.assertEqual(ratios, None)

        for i in range(0, 4):
            TickerStatementFactory(name=Statements.total_shareholder_equity,
                                   fiscal_date_ending=date.today() - relativedelta(months=i * 3),
                                   value=65000000000,
                                   ticker=ticker).save()
            TickerStatementFactory(name=Statements.total_assets,
                                   fiscal_date_ending=date.today() - relativedelta(months=i * 3),
                                   value=323000000000,
                                   ticker=ticker).save()

        serializer = TickerSerializer()
        ratios = serializer.get_returns_ratios(ticker)

        self.assertEqual(round(ratios['roa']), expected_roa)
        self.assertEqual(round(ratios['roe']), expected_roe)

    def test_outdated_tickers_manager(self):
        """
        Tests outdated tickers manager
        """
        self.assertEqual(Ticker.outdated_tickers.count(), 1)
