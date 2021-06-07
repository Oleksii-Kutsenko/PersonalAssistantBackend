"""
Parser for Invesco CSVs and related classes
"""
import json
from dataclasses import dataclass, asdict
from decimal import Decimal
from io import StringIO

import pandas as pd

from fin.models.index.parsers import Parser, TickerDataClass
from fin.models.ticker import Ticker
from .helpers import ParsedIndexTicker


@dataclass
class InvescoCSVTicker(TickerDataClass):
    """
    Class represents Invesco CSV raw ticker data
    """
    company_name: str
    cusip: str
    price: Decimal
    sector: str
    symbol: str

    def get_ticker(self):
        if (ticker_qs := Ticker.objects.filter(cusip=self.cusip)).exists():
            return ticker_qs.first()

        ticker_qs = Ticker.objects.filter(symbol=self.symbol)
        if ticker_qs.count() > 1:
            raise NotImplementedError('Cannot identify the stock security, there are need some extra actions')
        if ticker_qs.count() == 1:
            return ticker_qs.first()
        return Ticker.objects.create(**asdict(self))


@dataclass
class InvescoCSVIndexTicker(ParsedIndexTicker):
    """
    ParsedIndexTicker with InvescoCSVTicker
    """
    ticker: InvescoCSVTicker


class InvescoCSVParser(Parser):
    """
    Parser for Invesco indexes
    """
    updatable = False

    def __init__(self):
        self.csv_file = None

    def parse(self):
        cash_identifier = 'CASHUSD00'

        raw_index_ticker_rows = pd.read_csv(StringIO(self.csv_file), sep=',')
        index_ticker_rows = raw_index_ticker_rows[raw_index_ticker_rows['Security Identifier'] != cash_identifier]

        invesco_csv_index_tickers = []
        for _, row in index_ticker_rows.iterrows():
            invesco_csv_ticker = InvescoCSVTicker(
                company_name=row['Name'],
                cusip=row['Security Identifier'],
                symbol=row['Holding Ticker'],
                price=Decimal(row['MarketValue'].replace(',', '')) / int(row['Shares/Par Value'].replace(',', '')),
                sector=row['Sector']
            )
            invesco_csv_index_tickers.append(InvescoCSVIndexTicker(
                raw_data=json.loads(row.to_json()),
                ticker=invesco_csv_ticker,
                weight=row['Weight'])
            )
        return invesco_csv_index_tickers
