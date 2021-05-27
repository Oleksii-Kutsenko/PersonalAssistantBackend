"""
Parsers for indexes sources
"""
import csv
import io
from abc import ABC, abstractmethod
from decimal import Decimal
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
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
    NASDAQ100 = 'https://www.slickcharts.com/nasdaq100', _("NASDAQ 100")
    PBW = 'http://invescopowershares.com/products/overview.aspx?ticker=PBW', _("PBW")
    RUSSEL3000 = 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf' \
                 '/1467271812596.ajax', _('RUSSEL3000')
    SOXX = 'https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf' \
           '/1467271812596.ajax', _('SOXX')
    SP500 = 'https://www.slickcharts.com/sp500', _("S&P 500")


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
                'company_name': value, optional
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
        csv_file = pd.read_csv(io.StringIO(response.text))
        ibuy_csv_rows = csv_file[(csv_file['Account'] == index_name) & (csv_file['StockTicker'] != cash_ticker)]

        parsed_json = []
        for _, row in ibuy_csv_rows.iterrows():
            split_ticker_row = row['StockTicker'].split(' ')
            stock_exchange = Ticker.DEFAULT_VALUE
            if len(split_ticker_row) > 1:
                stock_exchange = self.exchanges[split_ticker_row[1]]
            symbol = split_ticker_row[0]

            parsed_json.append({
                'raw_data': row.to_json(),
                'ticker': {
                    'company_name': row['SecurityName'],
                    'symbol': symbol,
                    'price': row['Price'],
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
                'raw_data': row.to_json(),
                'ticker': {
                    'company_name': row['Name'],
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
        response = requests.get(self.source_url, params=self.params)

        equity_name = 'Equity'
        tickers_data_start_word = 'Ticker'
        tickers_data_start_index = response.text.find(tickers_data_start_word)
        tickers_data = StringIO(response.text[tickers_data_start_index:])

        total_market_cap = Decimal(0)
        parsed_json = []
        reader = csv.reader(tickers_data, delimiter=',')
        for row in reader:
            if len(row) > 2 and row[3] == equity_name:
                market_cap = Decimal(row[4].replace(',', ''))
                price = Decimal(row[11].replace(',', ''))
                if price == Decimal(0):
                    continue
                parsed_json.append({
                    'ticker': {
                        'price': price,
                        'market_cap': market_cap,
                        'stock_exchange': row[13],
                        'symbol': row[0]
                    },
                    'ticker_weight': None
                })
                total_market_cap += market_cap
        for ticker_json in parsed_json:
            ticker_json['ticker_weight'] = ticker_json['ticker']['market_cap'] / total_market_cap
        return parsed_json


class SlickChartsParser(Parser):
    """
    Parser for SlickCharts indexes
    """
    browser_headers = {'User-Agent': 'Magic Browser'}

    def __init__(self, source_url):
        self.source_url = source_url

    def parse(self):
        response = requests.get(self.source_url, headers=self.browser_headers)
        page = response.text

        page_html = BeautifulSoup(page, 'html.parser')
        tickers_table_classes = 'table table-hover table-borderless table-sm'
        tickers_table = page_html.find('table', class_=tickers_table_classes)
        tickers_rows = tickers_table.find('tbody')

        parsed_json = []
        for node in tickers_rows:
            if node.name == 'tr':
                tds = node.find_all('td')

                parsed_json.append({
                    'ticker': {
                        'company_name': str(tds[1].text),
                        'symbol': str(tds[2].text),
                        'price': Decimal(tds[4].text.replace(',', '')),
                    },
                    'ticker_weight': Decimal(tds[3].text)
                })
        return parsed_json
