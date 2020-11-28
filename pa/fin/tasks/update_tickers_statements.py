"""
The function that fetch information about ticker statements
"""
import logging

from redis.exceptions import LockError

from fin.external_api.alpha_vantage import AlphaVantage, AVFunctions
from fin.external_api.alpha_vantage.parsers import parse_time_series_monthly, parse_balance_sheet, \
    parse_income_statement
from fin.models.index import Index
from fin.models.utils import UpdatingStatus
from fin.models.portfolio import Portfolio
from fin.models.ticker import Ticker, TickerStatement
from pa import celery_app
from pa.celery import redis_client as r

logger = logging.getLogger(__name__)
LOCKED = 'Locked'


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
        pe_ratio = ticker_overview.get('PERatio')
        ticker.pe = None if pe_ratio == 'None' else pe_ratio

        ticker_income_statement = av_api.call(AVFunctions.income_statement.value,
                                              ticker.symbol)
        tickers_statements += parse_income_statement(ticker, ticker_income_statement)

        ticker_balance_sheet = av_api.call(AVFunctions.balance_sheet.value,
                                           ticker.symbol)
        tickers_statements += parse_balance_sheet(ticker, ticker_balance_sheet)

        ticker_time_series_monthly = av_api.call(AVFunctions.time_series_monthly_adjusted.value,
                                                 ticker.symbol)
        tickers_statements += parse_time_series_monthly(ticker, ticker_time_series_monthly)

        if tickers_statements:
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
    try:
        lock = r.lock('update_tickers_statements_task')
        if lock.acquire(blocking=False):
            update_tickers_statements(Ticker.outdated_tickers.all())
            lock.release()
            return True
        return LOCKED
    except LockError:
        return LOCKED


@celery_app.task()
def update_model_tickers_statements_task(obj_type, obj_id):
    """
    Updating tickers statements for given object type with given id
    """
    obj_types = {
        'Index': Index,
        'Portfolio': Portfolio
    }
    model = obj_types[obj_type]
    try:
        task_id = f'update_{obj_type}_{obj_id}_tickers_statements_task'
        lock = r.lock(task_id)
        if lock.acquire(blocking=False):
            obj = model.objects.get(pk=obj_id)
            obj.status = UpdatingStatus.updating
            obj.save()

            try:
                update_tickers_statements(obj.tickers.all())
            except Exception as error:
                logger.exception(error)
                logger.exception(obj.tickers.all())
                obj.status = UpdatingStatus.update_failed
                obj.save()
                lock.release()
                return False

            obj.status = UpdatingStatus.successfully_updated
            obj.save()
            lock.release()
            return True
        return LOCKED
    except LockError:
        return LOCKED
