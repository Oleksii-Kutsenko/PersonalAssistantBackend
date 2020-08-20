"""
Wrapper for AV API
"""
import json
import os
import time
from enum import Enum
from urllib.parse import urlencode, urlunsplit

import requests


class AVFunctions(Enum):
    """
    Supported functions of the AV API
    """
    balance_sheet = 'BALANCE_SHEET'
    cash_flow = 'CASH_FLOW'
    income_statement = 'INCOME_STATEMENT'
    overview = 'OVERVIEW'
    time_series_monthly_adjusted = 'TIME_SERIES_MONTHLY_ADJUSTED'


class AlphaVantage:
    """
    Class that make calls on AV API
    """
    SCHEME = 'https'
    NETLOC = 'www.alphavantage.co'
    PATH = '/query'
    await_message = 'Thank you for using Alpha Vantage! Our standard API call frequency is 5 ' \
                    'calls per minute and 500 calls per day. Please visit ' \
                    'https://www.alphavantage.co/premium/ if you would like to target a higher ' \
                    'API call frequency.'

    def __init__(self):
        self.apikey = os.environ.get('ALPHAVANTAGE_API_KEY')
        self.await_seconds = 0
        self.step = 60

    def call(self, function, symbol):
        """
        Construct URL based on parameters and make a request
        """
        query = urlencode(dict(function=function, symbol=symbol, apikey=self.apikey))
        url = urlunsplit((self.SCHEME, self.NETLOC, self.PATH, query, ''))

        response = requests.get(url)
        json_response = json.loads(response.text)
        while json_response.get('Note') and json_response.get('Note') == self.await_message:
            self.wait()
            response = requests.get(url)
            json_response = json.loads(response.text)
        return json_response

    def wait(self):
        """
        Snooze API requests for await_seconds
        """
        self.await_seconds += self.step
        time.sleep(self.await_seconds)
