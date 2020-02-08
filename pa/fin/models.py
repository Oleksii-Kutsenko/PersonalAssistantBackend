from bs4 import BeautifulSoup
from django.db import models
from django.utils.translation import gettext_lazy as _

import urllib.request


class TimeStampMixin(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(TimeStampMixin):
    """
    The model that represents an account
    """

    class Currency(models.TextChoices):
        UAH = 'UAH', _("Ukrainian Hryvnia")
        USD = 'USD', _("United States Dollar")
        EUR = 'EUR', _("Euro")

    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, choices=Currency.choices)


class Record(TimeStampMixin):
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)


class Index(TimeStampMixin):
    name = models.CharField(max_length=100)
    url = models.URLField()

    class Source(models.TextChoices):
        SLICK_CHARTS_SP500 = 'https://www.slickcharts.com/sp500'

    def recalculate(self):
        if self.Source.SLICK_CHARTS_SP500 == self.url:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Magic Browser'})
            page = urllib.request.urlopen(req).read().decode('utf-8')

            trs = BeautifulSoup(page, 'html.parser') \
                .find('table', class_='table table-hover table-borderless table-sm') \
                .find('tbody')

            for node in trs:
                if node.name == 'tr':
                    tds = node.find_all('td')
                    print(tds[2].text, tds[3].text, tds[4].text)


class Ticker(TimeStampMixin):
    name = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=7, decimal_places=7)
    deleted = models.BooleanField()
    index = models.ForeignKey(Index, on_delete=models.CASCADE)
