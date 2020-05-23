"""
Getting holders is wrapped into try-except block because sometimes this data is not available and it
isn't processing in any way
"""
import logging

import numpy as _np
import pandas as _pd
import yfinance.utils as utils
from yfinance import Ticker


class YFinanceTicker(Ticker):
    def _get_fundamentals(self, kind=None, proxy=None):
        def cleanup(data):
            df = _pd.DataFrame(data).drop(columns=['maxAge'])
            for col in df.columns:
                df[col] = _np.where(
                    df[col].astype(str) == '-', _np.nan, df[col])

            df.set_index('endDate', inplace=True)
            try:
                df.index = _pd.to_datetime(df.index, unit='s')
            except ValueError:
                df.index = _pd.to_datetime(df.index)
            df = df.T
            df.columns.name = ''
            df.index.name = 'Breakdown'

            df.index = utils.camel2title(df.index)
            return df

        # setup proxy in requests format
        if proxy is not None:
            if isinstance(proxy, dict) and "https" in proxy:
                proxy = proxy["https"]
            proxy = {"https": proxy}

        if self._fundamentals:
            return

        # get info and sustainability
        url = '%s/%s' % (self._scrape_url, self.ticker)
        data = utils.get_json(url, proxy)

        # holders
        url = "{}/{}/holders".format(self._scrape_url, self.ticker)
        try:
            holders = _pd.read_html(url)
            self._major_holders = holders[0]
            self._institutional_holders = holders[1]
            if 'Date Reported' in self._institutional_holders:
                self._institutional_holders['Date Reported'] = _pd.to_datetime(
                    self._institutional_holders['Date Reported'])
            if '% Out' in self._institutional_holders:
                self._institutional_holders['% Out'] = self._institutional_holders[
                                                           '% Out'].str.replace('%', '').astype(
                    float) / 100
        except (ValueError, IndexError) as error:
            logger = logging.getLogger(__name__)
            logger.info(self.ticker)
            logger.error(error)

        # sustainability
        d = {}
        if isinstance(data.get('esgScores'), dict):
            for item in data['esgScores']:
                if not isinstance(data['esgScores'][item], (dict, list)):
                    d[item] = data['esgScores'][item]

            s = _pd.DataFrame(index=[0], data=d)[-1:].T
            s.columns = ['Value']
            s.index.name = '%.f-%.f' % (
                s[s.index == 'ratingYear']['Value'].values[0],
                s[s.index == 'ratingMonth']['Value'].values[0])

            self._sustainability = s[~s.index.isin(
                ['maxAge', 'ratingYear', 'ratingMonth'])]

        # info (be nice to python 2)
        self._info = {}
        items = ['summaryProfile', 'summaryDetail', 'quoteType',
                 'defaultKeyStatistics', 'assetProfile', 'summaryDetail']
        for item in items:
            if isinstance(data.get(item), dict):
                self._info.update(data[item])

        self._info['regularMarketPrice'] = self._info['regularMarketOpen']
        self._info['logo_url'] = ""
        try:
            domain = self._info['website'].split(
                '://')[1].split('/')[0].replace('www.', '')
            self._info['logo_url'] = 'https://logo.clearbit.com/%s' % domain
        except Exception:
            pass

        # events
        try:
            cal = _pd.DataFrame(
                data['calendarEvents']['earnings'])
            cal['earningsDate'] = _pd.to_datetime(
                cal['earningsDate'], unit='s')
            self._calendar = cal.T
            self._calendar.index = utils.camel2title(self._calendar.index)
            self._calendar.columns = ['Value']
        except Exception:
            pass

        # analyst recommendations
        try:
            rec = _pd.DataFrame(
                data['upgradeDowngradeHistory']['history'])
            rec['earningsDate'] = _pd.to_datetime(
                rec['epochGradeDate'], unit='s')
            rec.set_index('earningsDate', inplace=True)
            rec.index.name = 'Date'
            rec.columns = utils.camel2title(rec.columns)
            self._recommendations = rec[[
                'Firm', 'To Grade', 'From Grade', 'Action']].sort_index()
        except Exception:
            pass

        # get fundamentals
        data = utils.get_json(url + '/financials', proxy)

        # generic patterns
        for key in (
                (self._cashflow, 'cashflowStatement', 'cashflowStatements'),
                (self._balancesheet, 'balanceSheet', 'balanceSheetStatements'),
                (self._financials, 'incomeStatement', 'incomeStatementHistory')
        ):

            item = key[1] + 'History'
            if isinstance(data.get(item), dict):
                key[0]['yearly'] = cleanup(data[item][key[2]])

            item = key[1] + 'HistoryQuarterly'
            if isinstance(data.get(item), dict):
                key[0]['quarterly'] = cleanup(data[item][key[2]])

        # earnings
        if isinstance(data.get('earnings'), dict):
            earnings = data['earnings']['financialsChart']
            df = _pd.DataFrame(earnings['yearly']).set_index('date')
            df.columns = utils.camel2title(df.columns)
            df.index.name = 'Year'
            self._earnings['yearly'] = df

            df = _pd.DataFrame(earnings['quarterly']).set_index('date')
            df.columns = utils.camel2title(df.columns)
            df.index.name = 'Quarter'
            self._earnings['quarterly'] = df

        self._fundamentals = True
