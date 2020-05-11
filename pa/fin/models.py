"""
Models
"""
import csv
import urllib.request
from decimal import Decimal
from io import StringIO

import requests
from bs4 import BeautifulSoup
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Sum, F, DecimalField, IntegerField, CharField, DateTimeField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from fin.utils.yf_patch import YFinanceTicker

MAX_DIGITS = 19
DECIMAL_PLACES = 2


class TimeStampMixin(models.Model):
    """
    Mixin for created, updated fields
    """
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)

    class Meta:
        """Meta"""
        abstract = True


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        """
        Available currencies for account
        """
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")
        EUR = 'EUR', _("Euro")

    name = CharField(max_length=100)
    currency = CharField(max_length=3, choices=Currency.choices)


class Record(TimeStampMixin):
    """
    Record model
    """
    amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)


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
        IHI = 'https://www.ishares.com/us/products/239516/' \
              'ishares-us-medical-devices-etf/1467271812596.ajax', _('IHI')

    data_source_url = models.URLField(choices=Source.choices, unique=True)

    def adjust(self, money, options):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = self.tickers \
            .exclude(country__in=options['skip_countries']) \
            .exclude(sector__in=options['skip_sectors']) \
            .exclude(industry__in=options['skip_industries']) \
            .exclude(symbol__in=options['skip_tickers']) \
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
        cost = Cast(F('amount') * F('price'), decimal_field)

        adjusted_money_amount = Decimal(money)
        step = Decimal(100)

        def amount():
            return Cast(F('weight') / 100 * adjusted_money_amount / F('price'), integer_field)

        summary_cost = 0
        while summary_cost < money:
            adjusted_money_amount += step
            tickers_query = tickers_query.annotate(amount=amount(), cost=cost)
            summary_cost = tickers_query.aggregate(Sum('cost')).get('cost__sum')

        adjusted_money_amount -= step
        tickers_query = tickers_query.annotate(amount=amount(), cost=cost)
        summary_cost = tickers_query.aggregate(Sum('cost')).get('cost__sum')

        # exclude not working on annotate field: "exclude(amount_neq=0)"
        result_query = [ticker for ticker in tickers_query if ticker.amount != 0]

        tickers_weight = sum([ticker.weight for ticker in result_query])
        coefficient = hundred_percent / tickers_weight
        for ticker in result_query:
            ticker.weight *= coefficient

        return result_query, summary_cost

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert=False, force_update=False, using=None, update_fields=None)
        self.update()

    def update(self):
        """
        Update tickers prices and their weights
        :return: None
        """
        browser_headers = {'User-Agent': 'Magic Browser'}
        if self.data_source_url in (self.Source.SP500, self.Source.NASDAQ100):
            req = urllib.request.Request(self.data_source_url, headers=browser_headers)
            with urllib.request.urlopen(req) as response:
                page = response.read().decode('utf-8')

            page_html = BeautifulSoup(page, 'html.parser')

            tickers_table_classes = 'table table-hover table-borderless table-sm'
            tickers_table = page_html.find('table', class_=tickers_table_classes)

            tickers_rows = tickers_table.find('tbody')

            self.tickers.all().delete()

            for node in tickers_rows:
                if node.name == 'tr':
                    tds = node.find_all('td')
                    ticker = Ticker(company=str(tds[1].text),
                                    symbol=str(tds[2].text),
                                    weight=Decimal(tds[3].text),
                                    price=Decimal(tds[4].text.replace(',', '')),
                                    index=self)
                    ticker.save()

        elif self.data_source_url == self.Source.IHI:
            ISHARES_IHI_PARAMS = {'fileType': 'csv', 'fileName': 'IHI_holdings', 'dataType': 'fund'}
            ISHARES_EQUITY_NAME = 'Equity'
            response = requests.get(self.data_source_url, params=ISHARES_IHI_PARAMS)

            tickers_data_start_word = 'Ticker'
            tickers_data_start_index = response.text.find(tickers_data_start_word)
            tickers_data = StringIO(response.text[tickers_data_start_index:])

            reader = csv.reader(tickers_data, delimiter=',')
            for row in reader:
                if len(row) > 2 and row[2] == ISHARES_EQUITY_NAME:
                    ticker = Ticker(symbol=row[0],
                                    company=row[1],
                                    weight=row[3],
                                    price=row[4],
                                    index=self)
                    ticker.save()

    def __str__(self):
        return str(dict(self.Source.choices)[self.data_source_url])


def update_tickers_industries(index_id):
    for ticker in Index.objects.get(pk=index_id).tickers.all():
        yf_ticker = YFinanceTicker(ticker.symbol.replace('.', '-'))
        ticker.country = yf_ticker.info.get('country', 'Unknown')
        ticker.industry = yf_ticker.info.get('industry', 'Unknown')
        ticker.sector = yf_ticker.info.get('sector', 'Unknown')
        ticker.save()


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    DEFAULT_VALUE = 'Unknown'

    company = models.CharField(max_length=50, default=DEFAULT_VALUE)
    country = models.CharField(max_length=50, default=DEFAULT_VALUE)
    index = models.ForeignKey(Index, related_name='tickers', on_delete=models.CASCADE)
    industry = models.CharField(max_length=50, default=DEFAULT_VALUE)
    price = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    sector = models.CharField(max_length=50, default=DEFAULT_VALUE)
    symbol = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=12, decimal_places=10,
                                 validators=[MinValueValidator(0.000001),
                                             MaxValueValidator(1.000001)])

    def __str__(self):
        return f"{self.symbol}"


class Goal(TimeStampMixin):
    """
    Goal model
    """
    name = CharField(max_length=100)
    coefficient = DecimalField(max_digits=3, decimal_places=DECIMAL_PLACES,
                               validators=[MinValueValidator(0.000001),
                                           MaxValueValidator(1.000001)])
    level = IntegerField(validators=[MinValueValidator(1)])
    current_money_amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                        validators=[MinValueValidator(0)])
    target_money_amount = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES,
                                       validators=[MinValueValidator(1)])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.current_money_amount == self.target_money_amount:
            self.target_money_amount *= (self.coefficient + Decimal(1))
            self.level += 1

        super(Goal, self).save(force_insert=False, force_update=False, using=None,
                               update_fields=None)
