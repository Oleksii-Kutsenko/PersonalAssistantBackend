"""
Helpers for parsers working
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


class Parser(ABC):
    """
    Parser basic class
    """
    updatable = True

    @abstractmethod
    def load_data(self):
        """
        Fetch raw data
        """

    @abstractmethod
    def parse(self):
        """
        Create data classes
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
