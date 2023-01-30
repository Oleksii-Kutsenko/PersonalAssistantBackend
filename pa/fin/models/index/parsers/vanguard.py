"""
Parser for Vanguard ETFs and related classes
"""
import operator
from dataclasses import dataclass, asdict
from decimal import Decimal
from functools import reduce

import pandas as pd
from django.db.models import Q

from fin.models.ticker import Ticker
from .helpers import (
    TickerDataClass,
    ParsedIndexTicker,
    Parser,
    KeysTickerDataClassMixin,
    ResolveDuplicatesMixin,
)


@dataclass
class VanguardTicker(TickerDataClass, KeysTickerDataClassMixin):
    """
    Class represents Vanguard raw ticker data
    """

    company_name: str
    cusip: str
    isin: str
    price: Decimal
    sedol: str
    symbol: str

    def get_ticker(self):
        keys = self.get_keys()
        ticker_qs = Ticker.objects.filter(
            reduce(operator.or_, [Q(**{k: v}) for k, v in keys.items()])
        )

        if ticker_qs.count() == 0:
            return Ticker.objects.create(**asdict(self))

        if ticker_qs.count() == 1:
            ticker = ticker_qs.first()
            ticker.price = self.price
            ticker.save()
            return ticker

        ticker_qs = ticker_qs.filter(symbol=self.symbol)
        if ticker_qs.count() == 0:
            raise NotImplementedError(f"Need further investigation - {asdict(self)}")

        if ticker_qs.count() == 1:
            ticker = ticker_qs.first()
            ticker.price = self.price
            ticker.save()
            return ticker
        raise NotImplementedError(f"Duplicated ticker - {asdict(self)}")


@dataclass
class VanguardIndexTicker(ParsedIndexTicker):
    """
    ParsedIndexTicker with VanguardTicker
    """

    ticker: VanguardTicker


class VanguardParser(Parser, ResolveDuplicatesMixin):
    """
    Parser for Vanguard indexes
    """

    updatable = False

    def __init__(self, _):
        self.raw_data = None

    def load_data(self):
        raise NotImplementedError

    def parse(self):
        dataframe = pd.DataFrame(self.raw_data)

        extra_columns = [
            "type",
            "asOfDate",
            "shortName",
            "notionalValue",
            "secMainType",
            "secSubType",
            "holdingType",
            "percentWeight",
        ]
        dataframe = dataframe.drop(columns=extra_columns)

        dataframe["sharesHeld"] = dataframe["sharesHeld"].astype("int32")
        dataframe["marketValue"] = dataframe["marketValue"].astype("float64")

        dataframe = dataframe[dataframe["marketValue"] != 0]
        total_cap = dataframe["marketValue"].sum()
        dataframe["weight"] = dataframe["marketValue"] / total_cap * 100

        vanguard_index_tickers = []
        for _, row in dataframe.iterrows():
            vanguard_index_ticker = VanguardTicker(
                company_name=row["longName"],
                cusip=row["cusip"],
                isin=row["isin"],
                price=Decimal(row["marketValue"] / row["sharesHeld"]),
                sedol=row["sedol"],
                symbol=row["ticker"],
            )
            vanguard_index_tickers.append(
                VanguardIndexTicker(
                    raw_data=row.to_dict(),
                    ticker=vanguard_index_ticker,
                    weight=row["weight"],
                )
            )

        filtered_index_tickers = self.resolve_duplicates(vanguard_index_tickers)
        return filtered_index_tickers
