"""
Parser for IShares ETFs and related classes
"""
import json
import operator
from dataclasses import dataclass, asdict
from decimal import Decimal
from functools import reduce
from io import StringIO

import pandas as pd
import requests
from django.db.models import Q

from fin.models.stock_exchange import StockExchangeAlias
from fin.models.ticker import Ticker
from .helpers import TickerDataClass, ParsedIndexTicker, Parser


# pylint: disable=too-many-instance-attributes
@dataclass
class ISharesTicker(TickerDataClass):
    """
    Class represents IShares raw ticker data
    """
    company_name: str
    cusip: str
    isin: str
    price: Decimal
    sector: str
    sedol: str
    stock_exchange_id: int
    symbol: str

    def get_ticker(self):
        keys = {
            k: v
            for k, v in {
                'cusip': self.cusip,
                'isin': self.isin,
                'sedol': self.sedol
            }.items()
            if v is not None
        }
        ticker_qs = Ticker.objects.filter(reduce(operator.and_, [Q(**{k: v}) for k, v in keys.items()]))
        if ticker_qs.count() == 1:
            return ticker_qs.first()

        # pylint: disable=too-many-boolean-expressions
        if ticker := Ticker.find_by_symbol_and_stock_exchange_id(self.symbol, self.stock_exchange_id):
            if (ticker.cusip and ticker.cusip == self.cusip) or \
                    (ticker.isin and ticker.isin == self.isin) or \
                    (ticker.sedol and ticker.sedol == self.sedol):
                return ticker
        # pylint: enable=too-many-boolean-expressions

        return Ticker.objects.create(**asdict(self))


# pylint: enable=too-many-instance-attributes

@dataclass
class ISharesIndexTicker(ParsedIndexTicker):
    """
    ParsedIndexTicker with ISharesTicker
    """
    ticker: ISharesTicker


class ISharesParser(Parser):
    """
    Parser for IShares indexes
    """

    def __init__(self, source):
        self.source_url = source.url
        self.params = source.isharessourceparams

    def parse(self):
        equity_name = 'Equity'
        tickers_data_start_word = 'Ticker'

        response = requests.get(self.source_url, params={'fileType': self.params.file_type,
                                                         'fileName': self.params.file_name,
                                                         'dataType': self.params.data_type})

        tickers_data_start_index = response.text.find(tickers_data_start_word)
        tickers_data = StringIO(response.text[tickers_data_start_index:])

        index_df = pd.read_csv(tickers_data, thousands=',')
        index_df = index_df[(index_df['Asset Class'] == equity_name) &
                            (index_df['Price'] > 0) &
                            (index_df['Ticker'] != '-') &
                            (index_df['Exchange'] != '-') &
                            (index_df['Exchange'] != 'NO MARKET (E.G. UNLISTED)') &
                            (index_df['Exchange'] != 'Non-Nms Quotation Service (Nnqs)')]

        index_df.loc[(index_df.CUSIP == '-'), 'CUSIP'] = None
        index_df.loc[(index_df.CUSIP == '-'), 'ISIN'] = None
        index_df.loc[(index_df.CUSIP == '-'), 'SEDOL'] = None

        index_df['Market Value'] = index_df['Market Value'].astype('float64')
        total_cap = index_df['Market Value'].sum()
        index_df['weight'] = index_df['Market Value'] / total_cap * 100

        stock_exchanges_mapper = dict(StockExchangeAlias.objects.values_list('alias', 'stock_exchange_id', ))

        ishares_index_tickers = []
        for _, row in index_df.iterrows():
            ishares_ticker = ISharesTicker(
                company_name=row.Name,
                cusip=row.CUSIP,
                isin=row.ISIN,
                price=row.Price,
                sector=row.Sector,
                sedol=row.SEDOL,
                stock_exchange_id=stock_exchanges_mapper[row.Exchange],
                symbol=row.Ticker,
            )
            ishares_index_tickers.append(ISharesIndexTicker(
                raw_data=json.loads(row.to_json()),
                ticker=ishares_ticker,
                weight=row.weight
            ))

        return ishares_index_tickers
