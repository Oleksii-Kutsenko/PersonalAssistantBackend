import json
import os
import pathlib
import urllib.request
import zipfile
from time import sleep
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand, CommandError
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver

from fin.models.index import Index


class Command(BaseCommand):
    help = 'Parse index with Selenium'

    def add_arguments(self, parser):
        parser.add_argument('data_source_name', nargs=1, type=str)

    @staticmethod
    def get_web_driver_path():
        current_path = pathlib.Path(__file__).parent.resolve()
        web_driver_dir = 'webdriver'
        web_driver_filename = 'chromedriver'

        web_driver_dir_path = os.path.join(current_path, web_driver_dir)
        web_driver_path = os.path.join(web_driver_dir_path, web_driver_filename)

        if not os.path.exists(web_driver_path):
            Command.download_web_driver(web_driver_dir_path)
            os.chmod(web_driver_path, 0o777)

        return web_driver_path

    @staticmethod
    def download_web_driver(path):
        os.makedirs(path, exist_ok=True)
        web_driver_url = 'https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_linux64.zip'
        local_filename, _ = urllib.request.urlretrieve(web_driver_url)
        with zipfile.ZipFile(local_filename, 'r') as web_driver_zip:
            web_driver_zip.extractall(path)

    @staticmethod
    @async_to_sync
    async def init_driver(web_driver_path):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(executable_path=web_driver_path, chrome_options=chrome_options)
        return driver

    @staticmethod
    @async_to_sync
    async def get_raw_index_tickers(driver):
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

    def handle(self, *args, **options):
        name = options['data_source_name'][0]

        try:
            index = Index.objects.get(source__name=name)
        except Index.DoesNotExist:
            raise CommandError('Index "%s" does not exist' % name)

        web_driver_path = self.get_web_driver_path()
        driver = self.init_driver(web_driver_path)
        index.source.parser.raw_data = self.get_raw_index_tickers(driver)

        parsed_index_tickers = index.source.parser.parse()
        index.update_from_parsed_index_tickers(parsed_index_tickers)

        self.stdout.write(self.style.SUCCESS('Successfully parsed "%s"' % name))
