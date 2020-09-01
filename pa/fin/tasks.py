"""
The function that fetch information about ticker statements
"""
import logging
from datetime import date, timedelta

from django.db.models import Q

from fin.external_api.alpha_vantage import AlphaVantage, AVFunctions
from fin.external_api.alpha_vantage.parsers import parse_time_series_monthly, parse_balance_sheet, \
    parse_income_statement
from fin.models.ticker import Ticker, TickerStatement, Statements
from pa import celery_app
from pa.celery import redis_lock

logger = logging.getLogger(__name__)


def update_tickers_statements(tickers_query):
    """
    The function gets tickers with the unknown sector, industry or country, or with outdated
    financial statements and trying to fetch this information from Alpha Vantage API
    """

    av_api = AlphaVantage()
    for ticker in tickers_query:
        tickers_statements = []

        ticker_overview = av_api.call(AVFunctions.overview.value, ticker.symbol)
        ticker.country = ticker_overview.get('Country', Ticker.DEFAULT_VALUE)
        ticker.industry = ticker_overview.get('Industry', Ticker.DEFAULT_VALUE)
        ticker.sector = ticker_overview.get('Sector', Ticker.DEFAULT_VALUE)

        ticker_income_statement = av_api.call(AVFunctions.income_statement.value,
                                              ticker.symbol)
        tickers_statements += parse_income_statement(ticker, ticker_income_statement)

        ticker_balance_sheet = av_api.call(AVFunctions.balance_sheet.value,
                                           ticker.symbol)
        tickers_statements += parse_balance_sheet(ticker, ticker_balance_sheet)

        ticker_time_series_monthly = av_api.call(AVFunctions.time_series_monthly_adjusted.value,
                                                 ticker.symbol)
        tickers_statements += parse_time_series_monthly(ticker, ticker_time_series_monthly)

        TickerStatement.objects.bulk_create(tickers_statements)
        ticker_price = ticker.ticker_statements \
            .filter(name='price') \
            .order_by('-fiscal_date_ending').first()
        ticker.price = ticker_price.value or ticker.price
        ticker.save()


@celery_app.task()
def update_tickers_statements_task():
    """
    Celery task wrapper for update_tickers_statements function
    """
    with redis_lock('update_tickers_statements_task') as acquired:
        if acquired:
            quarter_ago = date.today() - timedelta(30 * 3)
            tickers_query = Ticker.objects \
                .filter(Q(sector=Ticker.DEFAULT_VALUE) |
                        Q(industry=Ticker.DEFAULT_VALUE) |
                        Q(country=Ticker.DEFAULT_VALUE) |
                        Q(ticker_statements__name=Statements.net_income.value,
                          ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                        Q(ticker_statements__name=Statements.total_assets.value,
                          ticker_statements__fiscal_date_ending__lte=quarter_ago) |
                        Q(ticker_statements__name=Statements.price.value,
                          ticker_statements__fiscal_date_ending__lte=quarter_ago)) \
                .order_by('-ticker_statements__fiscal_date_ending')
            update_tickers_statements(tickers_query)
            return True
        logger.info('Update tickers statements task is already running')
        return False
