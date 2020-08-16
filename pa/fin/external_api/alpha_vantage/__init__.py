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

    def __init__(self, function, symbol):
        apikey = os.environ.get('ALPHAVANTAGE_API_KEY')
        query = urlencode(dict(function=function, symbol=symbol, apikey=apikey))
        url = urlunsplit((self.SCHEME, self.NETLOC, self.PATH, query, ''))

        response = requests.get(url)
        json_response = json.loads(response.text)
        await_seconds = 0
        step = 60
        while json_response.get('Note') and json_response.get('Note') == self.await_message:
            await_seconds += step
            time.sleep(await_seconds)
            response = requests.get(url)
            json_response = json.loads(response.text)
        self.data = json_response
