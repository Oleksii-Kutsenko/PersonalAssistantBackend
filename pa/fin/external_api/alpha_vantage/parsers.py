"""
Parsers for AV API
"""
from datetime import datetime

from fin.models.ticker import TickerStatement, Statements


def parse_time_series_monthly(ticker, ticker_time_series):
    """
    Parse JSON time series monthly response from AV API
    """
    tickers_statements = []
    for price_date, price_info in ticker_time_series.data['Monthly Adjusted Time Series'].items():
        date_obj = datetime.strptime(price_date, '%Y-%m-%d')
        tickers_statements += [TickerStatement(name=Statements.price.value,
                                               fiscal_date_ending=date_obj,
                                               value=price_info.get('5. adjusted close'),
                                               ticker=ticker)]
    return tickers_statements


def parse_balance_sheet(ticker, ticker_balance_sheet):
    """
    Parse JSON balance sheet response from AV API
    """
    tickers_statements = []
    for quarterly_report in ticker_balance_sheet.data.get('quarterlyReports'):
        fiscal_date_ending = datetime.strptime(quarterly_report.get('fiscalDateEnding'), '%Y-%m-%d')

        total_assets = quarterly_report.get('totalAssets')
        total_shareholder_equity = quarterly_report.get('totalShareholderEquity')

        total_long_term_debt = quarterly_report.get('totalLongTermDebt')
        total_long_term_debt = total_long_term_debt if total_long_term_debt != 'None' else 0

        short_term_debt = quarterly_report.get('shortTermDebt')
        short_term_debt = short_term_debt if short_term_debt != 'None' else 0

        cap_lease_obligations = quarterly_report.get('capitalLeaseObligations')
        cap_lease_obligations = cap_lease_obligations if cap_lease_obligations != 'None' else 0

        tickers_statements += [TickerStatement(name=Statements.total_assets.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=total_assets,
                                               ticker=ticker),
                               TickerStatement(name=Statements.total_shareholder_equity.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=total_shareholder_equity,
                                               ticker=ticker),
                               TickerStatement(name=Statements.total_long_term_debt.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=total_long_term_debt,
                                               ticker=ticker),
                               TickerStatement(name=Statements.short_term_debt.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=short_term_debt,
                                               ticker=ticker),
                               TickerStatement(name=Statements.capital_lease_obligations.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=cap_lease_obligations,
                                               ticker=ticker)]
    return tickers_statements


def parse_income_statement(ticker, ticker_income_statement):
    """
    Parse JSON income statement response from AV API
    """
    tickers_statements = []
    for quarterly_report in ticker_income_statement.data.get('quarterlyReports'):
        fiscal_date_ending = datetime.strptime(quarterly_report.get('fiscalDateEnding'), '%Y-%m-%d')
        net_income = quarterly_report.get('netIncome')
        total_revenue = quarterly_report.get('totalRevenue')

        tickers_statements += [TickerStatement(name=Statements.net_income.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=net_income,
                                               ticker=ticker),
                               TickerStatement(name=Statements.total_revenue.value,
                                               fiscal_date_ending=fiscal_date_ending,
                                               value=total_revenue,
                                               ticker=ticker)]
    return tickers_statements
