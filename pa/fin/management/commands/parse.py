import collections
import json
import os
import pathlib
import urllib.request
import zipfile
from decimal import Decimal
from time import sleep
from urllib.parse import parse_qs

import pandas as pd
from asgiref.sync import sync_to_async, async_to_sync
from django.core.management.base import BaseCommand, CommandError
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver

from fin.models.index import Index
from fin.models.index.parsers import VanguardTicker, VanguardIndexTicker


def get_index(name):
    return Index.objects.get(source__name=name)


class Command(BaseCommand):
    help = 'Parse index with Selenium'

    def add_arguments(self, parser):
        parser.add_argument('data_source_name', nargs=1, type=str)

    def handle(self, *args, **options):
        for name in options['data_source_name']:
            try:
                index = get_index(name)
            except Index.DoesNotExist:
                raise CommandError('Index "%s" does not exist' % name)

            current_path = pathlib.Path(__file__).parent.resolve()
            web_driver_dir = 'webdriver'
            web_driver_filename = 'chromedriver'
            web_driver_dir_path = os.path.join(current_path, web_driver_dir)
            web_driver_path = os.path.join(web_driver_dir_path, web_driver_filename)

            if not os.path.exists(web_driver_path):
                os.makedirs(web_driver_dir_path, exist_ok=True)

                web_driver_url = 'https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_linux64.zip'
                local_filename, _ = urllib.request.urlretrieve(web_driver_url)

                with zipfile.ZipFile(local_filename, 'r') as web_driver_zip:
                    web_driver_zip.extractall(web_driver_dir_path)

                os.chmod(web_driver_path, 0o777)

            raw_index_tickers = get_raw_index_tickers(web_driver_path)

            dataframe = pd.DataFrame(raw_index_tickers)
            dataframe = dataframe.drop(columns=['type', 'asOfDate', 'shortName', 'notionalValue', 'secMainType',
                                                'secSubType', 'holdingType', 'percentWeight'])

            dataframe['sharesHeld'] = dataframe['sharesHeld'].astype('int32')
            dataframe['marketValue'] = dataframe['marketValue'].astype('float64')
            dataframe = dataframe[dataframe['marketValue'] != 0]

            total_cap = dataframe['marketValue'].sum()
            dataframe['weight'] = dataframe['marketValue'] / total_cap * 100

            vanguard_index_tickers = []
            for _, row in dataframe.iterrows():
                vanguard_index_ticker = VanguardTicker(
                    company_name=row['longName'],
                    cusip=row['cusip'],
                    isin=row['isin'],
                    price=Decimal(row['marketValue'] / row['sharesHeld']),
                    sedol=row['sedol'],
                    symbol=row['ticker']
                )
                vanguard_index_tickers.append(VanguardIndexTicker(
                    raw_data=row.to_dict(),
                    ticker=vanguard_index_ticker,
                    weight=row['weight']
                ))

            duplicates = {}
            isin_s = [index_ticker.ticker.isin for index_ticker in vanguard_index_tickers]
            duplicates_isin_s = [item for item, count in collections.Counter(isin_s).items() if count > 1]
            filtered_index_tickers = []
            for vanguard_index_ticker in vanguard_index_tickers:
                if vanguard_index_ticker.ticker.isin in duplicates_isin_s:
                    if duplicates.get(vanguard_index_ticker.ticker.isin):
                        duplicates[vanguard_index_ticker.ticker.isin].append(vanguard_index_ticker)
                    else:
                        duplicates[vanguard_index_ticker.ticker.isin] = [vanguard_index_ticker]
                else:
                    filtered_index_tickers.append(vanguard_index_ticker)

            for key, value in duplicates.items():
                calculated_weight = sum([duplicate.weight for duplicate in value])
                value[0].weight = calculated_weight
                filtered_index_tickers.append(value[0])

            index.update_from_parsed_index_tickers(filtered_index_tickers)
            self.stdout.write(self.style.SUCCESS('Successfully parse "%s"' % name))


@async_to_sync
async def get_raw_index_tickers(web_driver_path):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(executable_path=web_driver_path, chrome_options=chrome_options)
    driver.get('https://investor.vanguard.com/etf/profile/overview/VT/portfolio-holdings')
    sleep(10)

    def check_url(url):
        return url.path.split('/')[-1] == 'stock.jsonp' and 'count' in parse_qs(url.querystring).keys()

    urls = [url for url in driver.requests if check_url(url)]
    raw_index_tickers = []
    for url in urls:
        response = url.response.body.decode('utf-8')
        raw_index_tickers += json.loads(response[21:-1])['fund']['entity']
    return raw_index_tickers
