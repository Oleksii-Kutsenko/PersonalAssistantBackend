"""
Helpers for parsers working
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Parser(ABC):
    """
    Parser basic class
    """
    updatable = True

    @abstractmethod
    def parse(self):
        """
        Fetch raw data and create data classes with it
        """


class TickerDataClass(ABC):
    """
    Interface for tickers dataclasses
    """

    @abstractmethod
    def get_ticker(self):
        """
        Try to get ticker from DB, if ticker does not exist in DB, creates new
        """


@dataclass
class ParsedIndexTicker:
    """
    Dataclass that represent raw IndexTicker relation
    """
    raw_data: dict
    ticker: None
    weight: Decimal


# pylint: disable=line-too-long
class Source(models.TextChoices):
    """
    Source for index data
    """
    IBUY = 'https://amplifyetfs.com/Data/Feeds/ForesideAmplify.40XL.XL_Holdings.csv', _('IBUY')
    IHI = 'https://www.ishares.com/us/products/239516/ishares-us-medical-devices-etf/1467271812596.ajax', _('IHI')
    ITOT = 'https://www.ishares.com/us/products/239724/ishares-core-sp-total-us-stock-market-etf/1467271812596.ajax', _(
        'ITOT')
    IXUS = 'https://www.ishares.com/us/products/244048/ishares-core-msci-total-international-stock-etf/1467271812596.ajax', _(
        'IXUS')
    PBW = 'http://invescopowershares.com/products/overview.aspx?ticker=PBW', _("PBW")
    RUSSEL3000 = 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax', _(
        'RUSSEL3000')
    SOXX = 'https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf/1467271812596.ajax', _('SOXX')
# pylint: enable=line-too-long
