"""
Parser for Amplify ETFs and related classes
"""
import io
import json
from dataclasses import dataclass, asdict
from decimal import Decimal

import pandas as pd
import requests

from fin.models.stock_exchange import StockExchangeAlias
from fin.models.ticker import Ticker
from .helpers import Parser, TickerDataClass, ParsedIndexTicker


@dataclass
class AmplifyTicker(TickerDataClass):
    """
    Class represents Amplify raw ticker data
    """
    company_name: str
    cusip: str
    stock_exchange_id: int
    symbol: str
    price: Decimal

    def get_ticker(self):
        if (ticker_qs := Ticker.objects.filter(cusip=self.cusip)).exists():
            return ticker_qs.first()

        if ticker := Ticker.find_by_symbol_and_stock_exchange_id(self.symbol, self.stock_exchange_id):
            if ticker.cusip is not None and ticker.cusip == self.cusip:
                return ticker

        return Ticker.objects.create(**asdict(self))


@dataclass
class AmplifyIndexTicker(ParsedIndexTicker):
    """
    ParsedIndexTicker with AmplifyTicker
    """
    ticker: AmplifyTicker


class AmplifyParser(Parser):
    """
    Parser for Amplify ETFs
    """
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'

    def __init__(self, source):
        self.source_url = source.url

    def parse(self):
        index_name = 'IBUY'
        cash_ticker = 'Cash&Other'
        stock_exchanges_mapper = dict(StockExchangeAlias.objects.values_list('alias', 'stock_exchange_id'))

        response = requests.get(self.source_url, headers={'User-Agent': self.user_agent})
        csv_file = pd.read_csv(io.StringIO(response.text), thousands=',')
        ibuy_csv_rows = csv_file[(csv_file['Account'] == index_name) & (csv_file['StockTicker'] != cash_ticker)]

        amplify_index_tickers = []
        for _, row in ibuy_csv_rows.iterrows():
            split_ticker_row = row['StockTicker'].split(' ')

            stock_exchange_id = None
            if len(split_ticker_row) > 1:
                stock_exchange_id = stock_exchanges_mapper[split_ticker_row[1]]
            symbol = split_ticker_row[0]

            amplify_ticker = AmplifyTicker(
                company_name=row.SecurityName,
                cusip=row.CUSIP,
                stock_exchange_id=(stock_exchange_id if stock_exchange_id else None),
                symbol=symbol,
                price=Decimal(row.MarketValue / row.Shares)
            )
            amplify_index_tickers.append(AmplifyIndexTicker(
                raw_data=json.loads(row.to_json()),
                ticker=amplify_ticker,
                weight=Decimal(row['Weightings'][:-1]))
            )
        return amplify_index_tickers
