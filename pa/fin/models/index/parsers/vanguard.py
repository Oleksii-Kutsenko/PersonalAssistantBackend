import operator
from dataclasses import dataclass, asdict
from decimal import Decimal
from functools import reduce

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
            import pdb
            pdb.set_trace()
            raise NotImplementedError(f'Duplicated ticker - {asdict(self)}')


@dataclass
class VanguardIndexTicker(ParsedIndexTicker):
    ticker: VanguardTicker


class VanguardParser(Parser):
    def parse(self):
        raise NotImplementedError
