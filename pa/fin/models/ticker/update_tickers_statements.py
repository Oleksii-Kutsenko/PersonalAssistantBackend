"""
The function that fetch information about ticker statements
"""
from datetime import date, timedelta

from django.db.models import Q

from fin.external_api.alpha_vantage import AlphaVantage, AVFunctions
from fin.external_api.alpha_vantage.parsers import parse_time_series_monthly, parse_balance_sheet, \
    parse_income_statement
from fin.models.ticker import Ticker, TickerStatement, Statements


def update_tickers_statements():
    """
    The function gets tickers with the unknown sector, industry or country, or with outdated
    financial statements and trying to fetch this information from Alpha Vantage API
    """
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

    for ticker in tickers_query:
        tickers_statements = []

        ticker_overview = AlphaVantage(AVFunctions.overview.value, ticker.symbol)
        ticker.country = ticker_overview.data.get('Country', Ticker.DEFAULT_VALUE)
        ticker.industry = ticker_overview.data.get('Industry', Ticker.DEFAULT_VALUE)
        ticker.sector = ticker_overview.data.get('Sector', Ticker.DEFAULT_VALUE)

        ticker_income_statement = AlphaVantage(AVFunctions.income_statement.value,
                                               ticker.symbol)
        tickers_statements += parse_income_statement(ticker, ticker_income_statement)

        ticker_balance_sheet = AlphaVantage(AVFunctions.balance_sheet.value,
                                            ticker.symbol)
        tickers_statements += parse_balance_sheet(ticker, ticker_balance_sheet)

        ticker_time_series_monthly = AlphaVantage(AVFunctions.time_series_monthly_adjusted.value,
                                                  ticker.symbol)
        tickers_statements += parse_time_series_monthly(ticker, ticker_time_series_monthly)

        TickerStatement.objects.bulk_create(tickers_statements)
        ticker.save()
