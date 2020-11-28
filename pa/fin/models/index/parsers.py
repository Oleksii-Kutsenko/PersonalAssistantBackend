"""
Parsers for indexes sources
"""
import csv

from abc import ABC, abstractmethod
from decimal import Decimal
from io import StringIO

import requests
from bs4 import BeautifulSoup
from django.db import models
from django.utils.translation import gettext_lazy as _
from yfinance import Ticker


class Source(models.TextChoices):
    """
    Source for index data
    """
    IHI = 'https://www.ishares.com/us/products/239516/ishares-us-medical-devices-etf' \
          '/1467271812596.ajax', _('IHI')
    NASDAQ100 = 'https://www.slickcharts.com/nasdaq100', _("NASDAQ 100")
    PBW = 'http://invescopowershares.com/products/overview.aspx?ticker=PBW', _("PBW")
    RUSSEL3000 = 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf' \
                 '/1467271812596.ajax', _('RUSSEL3000')
    SOXX = 'https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf' \
           '/1467271812596.ajax', _('SOXX')
    SP500 = 'https://www.slickcharts.com/sp500', _("S&P 500")


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
            'ticker': {
                'company_name': value, optional
                'symbol': value, required
                'price': value, optional
                'market_cap': market_cap, optional
            },
            'ticker_weight': value
        }
        """


class InvescoCSVParser(Parser):
    """
    Parser for Invesco indexes
    """
    updatable = False

    def __init__(self):
        self.csv_file = None

    def set_csv_file(self, csv_file):
        """
        Set CSV File which contains index data
        """
        self.csv_file = csv_file

    def parse(self):
        parsed_json = []

        file_strings = self.csv_file.splitlines()
        reader = csv.reader(file_strings)
        first_row_id = 'Fund Ticker'

        for row in reader:
            if row[0] != first_row_id:
                symbol = row[2].strip()
                ticker = Ticker(symbol)
                parsed_json.append({
                    'ticker': {
                        'company_name': row[6],
                        'symbol': symbol,
                        'price': ticker.info.get('ask')
                    },
                    'ticker_weight': row[5]
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
