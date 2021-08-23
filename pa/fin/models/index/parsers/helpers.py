"""
Helpers for parsers working
"""
import collections
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


class KeysTickerDataClassMixin:
    """
    Mixin for function inheritance
    """

    def get_keys(self):
        """
        Returns keys for database searching
        """
        return {
            k: v
            for k, v in {
                'cusip': self.cusip,
                'isin': self.isin,
                'sedol': self.sedol
            }.items()
            if v is not None and v != ''
        }


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


@dataclass
class ParsedIndexTicker:
    """
    Dataclass that represent raw IndexTicker relation
    """
    raw_data: dict
    ticker: None
    weight: Decimal


class ResolveDuplicatesMixin:
    @staticmethod
    def resolve_duplicates(ishares_index_tickers):
        duplicates = {}
        isin_s = [index_ticker.ticker.isin for index_ticker in ishares_index_tickers]
        duplicates_isin_s = [item for item, count in collections.Counter(isin_s).items() if count > 1]

        filtered_index_tickers = []
        for index_ticker in ishares_index_tickers:
            if index_ticker.ticker.isin in duplicates_isin_s:
                if duplicates.get(index_ticker.ticker.isin):
                    duplicates[index_ticker.ticker.isin].append(index_ticker)
                else:
                    duplicates[index_ticker.ticker.isin] = [index_ticker]
            else:
                filtered_index_tickers.append(index_ticker)

        for _, value in duplicates.items():
            calculated_weight = sum([duplicate.weight for duplicate in value])
            value[0].weight = calculated_weight
            filtered_index_tickers.append(value[0])

        return filtered_index_tickers


class TickerDataClass(ABC):
    """
    Interface for tickers dataclasses
    """

    @abstractmethod
    def get_ticker(self):
        """
        Try to get ticker from DB, if ticker does not exist in DB, creates new
        """
