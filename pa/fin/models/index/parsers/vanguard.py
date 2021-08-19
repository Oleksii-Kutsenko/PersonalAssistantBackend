import collections
import operator
from dataclasses import dataclass, asdict
from decimal import Decimal
from functools import reduce

import pandas as pd
from django.db.models import Q

from fin.models.ticker import Ticker
from .helpers import TickerDataClass, ParsedIndexTicker, Parser


@dataclass
class VanguardTicker(TickerDataClass):
    company_name: str
    cusip: str
    isin: str
    price: Decimal
    sedol: str
    symbol: str

    def get_ticker(self):
        keys = {
            k: v
            for k, v in {
                'cusip': self.cusip,
                'isin': self.isin,
                'sedol': self.sedol
            }.items()
            if v is not None and v != ''
        }
        ticker_qs = Ticker.objects.filter(reduce(operator.or_, [Q(**{k: v}) for k, v in keys.items()]))
        if ticker_qs.count() == 0:
            return Ticker.objects.create(**asdict(self))
        elif ticker_qs.count() == 1:
            ticker = ticker_qs.first()
            ticker.price = self.price
            ticker.save()
            return ticker
        else:
            ticker_qs = ticker_qs.filter(symbol=self.symbol)
            if ticker_qs.count() == 0:
                return Ticker.objects.create(**asdict(self))
            elif ticker_qs.count() == 1:
                ticker = ticker_qs.first()
                ticker.price = self.price
                ticker.save()
                return ticker
            raise NotImplementedError(f'Duplicated ticker - {asdict(self)}')


@dataclass
class VanguardIndexTicker(ParsedIndexTicker):
    ticker: VanguardTicker


class VanguardParser(Parser):
    updatable = False

    def __init__(self, _):
        self.raw_data = None

    def load_data(self):
        raise NotImplementedError

    def parse(self):
        dataframe = pd.DataFrame(self.raw_data)

        extra_columns = ['type', 'asOfDate', 'shortName', 'notionalValue', 'secMainType', 'secSubType', 'holdingType',
                         'percentWeight']
        dataframe = dataframe.drop(columns=extra_columns)

        dataframe['sharesHeld'] = dataframe['sharesHeld'].astype('int32')
        dataframe['marketValue'] = dataframe['marketValue'].astype('float64')

        dataframe = dataframe[dataframe['marketValue'] != 0]
        total_cap = dataframe['marketValue'].sum()
        dataframe['weight'] = dataframe['marketValue'] / total_cap * 100

        vanguard_index_tickers = []
        for _, row in dataframe.iterrows():
            vanguard_index_ticker = VanguardTicker(
                company_name=row['longName'],
                cusip=row['cusip'],
                isin=row['isin'],
                price=Decimal(row['marketValue'] / row['sharesHeld']),
                sedol=row['sedol'],
                symbol=row['ticker']
            )
            vanguard_index_tickers.append(VanguardIndexTicker(
                raw_data=row.to_dict(),
                ticker=vanguard_index_ticker,
                weight=row['weight']
            ))

        filtered_index_tickers = self.resolve_duplicates(vanguard_index_tickers)
        return filtered_index_tickers

    @staticmethod
    def resolve_duplicates(vanguard_index_tickers):
        duplicates = {}
        isin_s = [index_ticker.ticker.isin for index_ticker in vanguard_index_tickers]
        duplicates_isin_s = [item for item, count in collections.Counter(isin_s).items() if count > 1]
        filtered_index_tickers = []
        for vanguard_index_ticker in vanguard_index_tickers:
            if vanguard_index_ticker.ticker.isin in duplicates_isin_s:
                if duplicates.get(vanguard_index_ticker.ticker.isin):
                    duplicates[vanguard_index_ticker.ticker.isin].append(vanguard_index_ticker)
                else:
                    duplicates[vanguard_index_ticker.ticker.isin] = [vanguard_index_ticker]
            else:
                filtered_index_tickers.append(vanguard_index_ticker)
        for key, value in duplicates.items():
            calculated_weight = sum([duplicate.weight for duplicate in value])
            value[0].weight = calculated_weight
            filtered_index_tickers.append(value[0])
        return filtered_index_tickers
