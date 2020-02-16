"""
Models
"""
from decimal import Decimal
import urllib.request

from bs4 import BeautifulSoup
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Min
from django.utils.translation import gettext_lazy as _


class TimeStampMixin(models.Model):
    """
    Mixin for created, updated fields
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

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

    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, choices=Currency.choices)


class Record(TimeStampMixin):
    """
    Record model
    """
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)


class Index(TimeStampMixin):
    """
    Index model
    """

    class Source(models.TextChoices):
        """
        Source for index data
        """
        SLICK_CHARTS_SP500 = 'https://www.slickcharts.com/sp500', _("S&P 500")

    data_source_url = models.URLField(choices=Source.choices, unique=True)

    @property
    def tickers_last_updated(self):
        """
        Returns datetime when tickers were last updated
        """
        return self.tickers.aggregate(Min('updated')).get('updated__min')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super(Index, self).save(force_insert=False, force_update=False, using=None,
                                update_fields=None)
        self.update()

    def update(self):
        """
        Update tickers prices and their weights
        :return: None
        """
        if self.Source.SLICK_CHARTS_SP500 == self.data_source_url:
            req = urllib.request.Request(self.data_source_url,
                                         headers={'User-Agent': 'Magic Browser'})
            page = urllib.request.urlopen(req).read().decode('utf-8')

            trs = BeautifulSoup(page, 'html.parser') \
                .find('table', class_='table table-hover table-borderless table-sm') \
                .find('tbody')

            self.tickers.all().delete()

            for node in trs:
                if node.name == 'tr':
                    tds = node.find_all('td')
                    ticker = Ticker(name=str(tds[2].text),
                                    weight=Decimal(tds[3].text),
                                    price=Decimal(tds[4].text.replace(',', '')),
                                    index=self)
                    ticker.save()

    def __str__(self):
        return str(dict(self.Source.choices)[self.data_source_url])


class Ticker(TimeStampMixin):
    """
    Ticker model
    """
    name = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=12, decimal_places=10,
                                 validators=[MinValueValidator(0.000001),
                                             MaxValueValidator(1.000001)])
    price = models.DecimalField(max_digits=19, decimal_places=2)
    index = models.ForeignKey(Index, related_name='tickers', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}"


class Goal(TimeStampMixin):
    """
    Goal model
    """
    name = models.CharField(max_length=100)
    coefficient = models.DecimalField(max_digits=3, decimal_places=2,
                                      validators=[MinValueValidator(0.000001),
                                                  MaxValueValidator(1.000001)])
    current_money_amount = models.DecimalField(max_digits=19, decimal_places=2,
                                               validators=[MinValueValidator(0)])
    target_money_amount = models.DecimalField(max_digits=19, decimal_places=2,
                                              validators=[MinValueValidator(1)])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.current_money_amount == self.target_money_amount:
            self.target_money_amount *= (self.coefficient + Decimal(1))
        super(Goal, self).save(force_insert=False, force_update=False, using=None,
                               update_fields=None)
