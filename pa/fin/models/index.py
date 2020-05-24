import csv
import urllib.request
from decimal import Decimal
from io import StringIO

import requests
from bs4 import BeautifulSoup
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import DecimalField, Sum, F
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from fin.models.models import MAX_DIGITS, DECIMAL_PLACES
from fin.models.utils import TimeStampMixin


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    DEFAULT_VALUE = 'Unknown'

    company_name = models.CharField(max_length=50, default=DEFAULT_VALUE)
    country = models.CharField(max_length=50, default=DEFAULT_VALUE)
    industry = models.CharField(max_length=50, default=DEFAULT_VALUE)
    market_cap = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True)
    price = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    sector = models.CharField(max_length=50, default=DEFAULT_VALUE)
    symbol = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.symbol}"


class Index(TimeStampMixin):
    """
    Index model
    """

    class Source(models.TextChoices):
        """
        Source for index data
        """
        SP500 = 'https://www.slickcharts.com/sp500', _("S&P 500")
        NASDAQ100 = 'https://www.slickcharts.com/nasdaq100', _("NASDAQ 100")
        IHI = 'https://www.ishares.com/us/products/239516/ishares-us-medical-devices-etf/1467271812596.ajax', _('IHI')
        RUSSEL3000 = 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax', \
                     _('RUSSEL3000')

    data_source_url = models.URLField(choices=Source.choices, unique=True)
    tickers = models.ManyToManyField(Ticker, through='TickerIndexWeight')

    @transaction.atomic
    def adjust(self, money, options):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = TickerIndexWeight.objects.filter(index=self) \
            .exclude(ticker__country__in=options['skip_countries']) \
            .exclude(ticker__sector__in=options['skip_sectors']) \
            .exclude(ticker__industry__in=options['skip_industries']) \
            .exclude(ticker__symbol__in=options['skip_tickers']) \
            .order_by('-weight')

        # adjust sum of weights to 100%
        hundred_percent = Decimal(100)
        tickers_weight = tickers_query.aggregate(Sum('weight')).get('weight__sum')
        coefficient = hundred_percent / tickers_weight

        for ticker in tickers_query:
            ticker.weight *= coefficient

        # compute amount
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        integer_field = models.IntegerField()
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        adjusted_money_amount = Decimal(money)
        step = Decimal(100)

        def amount():
            return Cast(F('weight') / 100 * adjusted_money_amount / F('ticker__price'), integer_field)

        summary_cost = 0
        while summary_cost < money:
            adjusted_money_amount += step
            tickers_query = tickers_query.annotate(amount=amount(), cost=cost)

            summary_cost = tickers_query.aggregate(Sum('cost')).get('cost__sum')

        adjusted_money_amount -= step
        tickers_query = tickers_query.annotate(amount=amount(), cost=cost)
        summary_cost = tickers_query.aggregate(Sum('cost')).get('cost__sum')

        # adjust sum of weights to 100%
        tickers_query = tickers_query.filter(amount__gt=0)
        tickers_weight = tickers_query.aggregate(Sum('weight')).get('weight__sum')
        coefficient = hundred_percent / tickers_weight

        for ticker in tickers_query:
            ticker.weight *= coefficient

        return tickers_query, summary_cost

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert=False, force_update=False, using=None, update_fields=None)
        self.update()

    @transaction.atomic
    def update(self):
        """
        Update tickers prices and their weights
        :return: None
        """
        if self.data_source_url in (self.Source.SP500, self.Source.NASDAQ100):
            browser_headers = {'User-Agent': 'Magic Browser'}

            req = urllib.request.Request(self.data_source_url, headers=browser_headers)
            with urllib.request.urlopen(req) as response:
                page = response.read().decode('utf-8')

            page_html = BeautifulSoup(page, 'html.parser')

            tickers_table_classes = 'table table-hover table-borderless table-sm'
            tickers_table = page_html.find('table', class_=tickers_table_classes)

            tickers_rows = tickers_table.find('tbody')

            for node in tickers_rows:
                if node.name == 'tr':
                    tds = node.find_all('td')

                    symbol = str(tds[2].text)
                    ticker_info = {
                        'company_name': str(tds[1].text),
                        'price': Decimal(tds[4].text.replace(',', ''))
                    }

                    ticker, _ = Ticker.objects.update_or_create(symbol=symbol, defaults=ticker_info)
                    ticker.save()

                    ticker_weight = Decimal(tds[3].text)
                    ticker_index_relation = TickerIndexWeight(index=self, ticker=ticker, weight=ticker_weight)
                    ticker_index_relation.save()

        elif self.data_source_url in (self.Source.IHI, self.Source.RUSSEL3000):
            IHI_PARAMS = {'fileType': 'csv', 'fileName': 'IHI_holdings', 'dataType': 'fund'}
            RUSSEL_PARAMS = {'fileType': 'csv', 'fileName': 'IWV_holdings', 'dataType': 'fund'}

            if self.data_source_url == self.Source.IHI:
                params = IHI_PARAMS
            else:
                params = RUSSEL_PARAMS

            EQUITY_NAME = 'Equity'
            response = requests.get(self.data_source_url, params=params)

            tickers_data_start_word = 'Ticker'
            tickers_data_start_index = response.text.find(tickers_data_start_word)
            tickers_data = StringIO(response.text[tickers_data_start_index:])

            self.tickers.all().delete()

            total_market_cap = Decimal(0)
            reader = csv.reader(tickers_data, delimiter=',')
            for row in reader:
                if len(row) > 2 and row[2] == EQUITY_NAME:
                    price_without_separators = Decimal(row[4].replace(',', ''))
                    if price_without_separators != Decimal(0):
                        market_cap_without_separators = Decimal(row[6].replace(',', ''))

                        symbol = row[0]
                        ticker_info = {
                            'company_name': row[1],
                            'price': price_without_separators,
                            'market_cap': market_cap_without_separators
                        }
                        ticker, _ = Ticker.objects.update_or_create(symbol=symbol, defaults=ticker_info)
                        ticker.save()

                        ticker_weight = Decimal(row[3])
                        ticker_index_relation = TickerIndexWeight(index=self, ticker=ticker, weight=ticker_weight)
                        ticker_index_relation.save()
                        total_market_cap += market_cap_without_separators

            for ticker_index_weight in TickerIndexWeight.objects.filter(index=self):
                ticker_index_weight.weight = ticker_index_weight.ticker.market_cap / total_market_cap
                ticker_index_weight.save()

    def __str__(self):
        return str(dict(self.Source.choices)[self.data_source_url])


class TickerIndexWeight(TimeStampMixin):
    index = models.ForeignKey(Index, on_delete=models.CASCADE, related_name='index')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE, related_name='ticker')
    weight = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=10, validators=[MinValueValidator(0.000001),
                                                                                       MaxValueValidator(1.000001)])
