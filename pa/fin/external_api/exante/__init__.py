"""
Helpers for EXANTE API
"""
import datetime
import os
import time

import jwt
import requests


def get_jwt(iss=os.environ.get('ISS'), sub=os.environ.get('SUB'), key=os.environ.get('KEY')):
    """
    Generate jwt for EXANTE API
    """
    return jwt.encode({'sub': sub,
                       'iss': iss,
                       'iat': int(time.mktime(datetime.datetime.utcnow().timetuple())),
                       'exp': int(time.mktime((datetime.datetime.utcnow() + datetime.timedelta(days=1)).timetuple())),
                       'aud': [
                           "symbols",
                           "ohlc",
                           "feed",
                           "change",
                           "crossrates",
                           "orders",
                           "summary",
                           "accounts",
                           "transactions"
                       ]},
                      key)


def get_account_summary(token):
    """
    Returns account summary in json format
    """
    version = '3.0'
    account_id = 'UJE7173.178'
    currency = 'USD'
    return requests.get(f'https://api-live.exante.eu/md/{version}/summary/{account_id}/{currency}/',
                        headers={'Authorization': f'Bearer {token}'}).json()
