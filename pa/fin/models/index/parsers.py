"""
Parsers for indexes sources
"""
import io
import json
from abc import ABC, abstractmethod
from decimal import Decimal
from io import StringIO

import pandas as pd
import requests
from django.db import models
from django.utils.translation import gettext_lazy as _

from fin.models.ticker import Ticker


# pylint: disable=line-too-long
class Source(models.TextChoices):
    """
    Source for index data
    """
    IBUY = 'https://amplifyetfs.com/Data/Feeds/ForesideAmplify.40XL.XL_Holdings.csv', _('IBUY')
    IHI = 'https://www.ishares.com/us/products/239516/ishares-us-medical-devices-etf' \
          '/1467271812596.ajax', _('IHI')
    ITOT = 'https://www.ishares.com/us/products/239724/ishares-core-sp-total-us-stock-market-etf/1467271812596.ajax', \
           _('ITOT')
    IXUS = 'https://www.ishares.com/us/products/244048/ishares-core-msci-total-international-stock-etf/1467271812596.ajax', \
           _('IXUS')
    PBW = 'http://invescopowershares.com/products/overview.aspx?ticker=PBW', _("PBW")
    RUSSEL3000 = 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf' \
                 '/1467271812596.ajax', _('RUSSEL3000')
    SOXX = 'https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf' \
           '/1467271812596.ajax', _('SOXX')


# pylint: enable=line-too-long

class Parser(ABC):
    """
    Parser basic class
    """
    updatable = True

    @abstractmethod
    def parse(self):
        """
        Fetch raw data and uniform it in format
        {
            'raw_data': { ...data... },
            'ticker': {
                'company_name': value, optional,
                'cusip', value, optional
                'symbol': value, required
                'price': value, optional
                'market_cap': market_cap, optional,
                'stock_exchange': name, required,
                'sector': name, optional,
            },
            'ticker_weight': value
        }
        """


class AmplifyParser(Parser):
    exchanges = {
        'GR': 'Xetra',
        'JP': 'Tokyo Stock Exchange',
        'LN': 'London Stock Exchange',
        'NA': 'Euronext Amsterdam'
    }

    def __init__(self, source_url):
        self.source_url = source_url

    def parse(self):
        index_name = 'IBUY'
        cash_ticker = 'Cash&Other'
        response = requests.get(self.source_url)
        csv_file = pd.read_csv(io.StringIO(response.text), thousands=',')
        ibuy_csv_rows = csv_file[(csv_file['Account'] == index_name) & (csv_file['StockTicker'] != cash_ticker)]

        parsed_json = []
        for _, row in ibuy_csv_rows.iterrows():
            split_ticker_row = row['StockTicker'].split(' ')
            stock_exchange = Ticker.DEFAULT_VALUE
            if len(split_ticker_row) > 1:
                stock_exchange = self.exchanges[split_ticker_row[1]]
            symbol = split_ticker_row[0]

            parsed_json.append({
                'raw_data': json.loads(row.to_json()),
                'ticker': {
                    'company_name': row['SecurityName'],
                    'cusip': row['CUSIP'],
                    'symbol': symbol,
                    'price': row['MarketValue'] / row['Shares'],
                    'market_cap': row['MarketValue'],
                    'stock_exchange': stock_exchange
                },
                'ticker_weight': Decimal(row['Weightings'][:-1])
            })

        return parsed_json


class InvescoCSVParser(Parser):
    """
    Parser for Invesco indexes
    """
    updatable = False

    def __init__(self):
        self.csv_file = None

    def parse(self):
        cash_identifier = 'CASHUSD00'
        parsed_json = []

        raw_index_ticker_rows = pd.read_csv(StringIO(self.csv_file), sep=',')
        index_ticker_rows = raw_index_ticker_rows[raw_index_ticker_rows['Security Identifier'] != cash_identifier]
        for _, row in index_ticker_rows.iterrows():
            parsed_json.append({
                'raw_data': json.loads(row.to_json()),
                'ticker': {
                    'company_name': row['Name'],
                    'cusip': row['Security Identifier'],
                    'symbol': row['Holding Ticker'],
                    'price': float(row['MarketValue'].replace(',', '')) / int(row['Shares/Par Value'].replace(',', '')),
                    'market_cap': row['MarketValue'].replace(',', ''),
                    'stock_exchange': Ticker.DEFAULT_VALUE,
                    'sector': row['Sector']
                },
                'ticker_weight': row['Weight']
            })
        return parsed_json


class ISharesParser(Parser):
    """
    Parser for IShares indexes
    """
    index_params = {
        Source.IHI.value: {'fileType': 'csv',
                           'fileName': 'IHI_holdings',
                           'dataType': 'fund'},
        Source.ITOT.value: {'fileType': 'csv',
                            'fileName': 'ITOT_holdings',
                            'dataType': 'fund'},
        Source.IXUS.value: {'fileType': 'csv',
                            'fileName': 'IXUS_holdings',
                            'dataType': 'fund'},
        Source.RUSSEL3000.value: {'fileType': 'csv',
                                  'fileName': 'IWV_holdings',
                                  'dataType': 'fund'},
        Source.SOXX.value: {'fileType': 'csv',
                            'fileName': 'SOXX_holdings',
                            'dataType': 'fund'}
    }

    def __init__(self, source_url):
        self.source_url = source_url
        self.params = self.index_params[source_url]

    def parse(self):
        parsed_json = []
        equity_name = 'Equity'
        tickers_data_start_word = 'Ticker'

        response = requests.get(self.source_url, params=self.params)

        tickers_data_start_index = response.text.find(tickers_data_start_word)
        tickers_data = StringIO(response.text[tickers_data_start_index:])

        index_df = pd.read_csv(tickers_data, thousands=',')
        index_df = index_df[(index_df['Asset Class'] == equity_name) &
                            (index_df['Price'] > 0) &
                            (index_df['Ticker'] != '-')]

        index_df.loc[(index_df.CUSIP == '-'), 'CUSIP'] = None
        index_df.loc[(index_df.CUSIP == '-'), 'ISIN'] = None
        index_df.loc[(index_df.CUSIP == '-'), 'SEDOL'] = None

        index_df['Market Value'] = index_df['Market Value'].astype('float64')
        total_cap = index_df['Market Value'].sum()
        index_df['weight'] = index_df['Market Value'] / total_cap * 100

        for _, row in index_df.iterrows():
            parsed_json.append({
                'raw_data': json.loads(row.to_json()),
                'ticker': {
                    'company_name': row['Name'],
                    'cusip': row['CUSIP'],
                    'isin': row['ISIN'],
                    'price': row['Price'],
                    'sector': row['Sector'],
                    'sedol': row['SEDOL'],
                    'stock_exchange': row['Exchange'],
                    'symbol': row['Ticker'],
                },
                'ticker_weight': row['weight']
            })

        return parsed_json
