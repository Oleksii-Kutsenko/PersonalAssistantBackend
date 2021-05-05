"""
Classes that helps operate with indexes and tickers
"""

import numpy as np
import pandas as pd
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Q

from fin.models.index.parsers import SlickChartsParser, ISharesParser, Source, InvescoCSVParser, AmplifyParser
from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, UpdatingStatus


class Index(TimeStampMixin):
    """
    Index model
    """

    url_parsers = {
        Source.IBUY.value: AmplifyParser(Source.IBUY.value),
        Source.IHI.value: ISharesParser(Source.IHI.value),
        Source.ITOT.value: ISharesParser(Source.ITOT.value),
        Source.IXUS.value: ISharesParser(Source.IXUS.value),
        Source.NASDAQ100.value: SlickChartsParser(Source.NASDAQ100.value),
        Source.PBW.value: InvescoCSVParser(),
        Source.RUSSEL3000.value: ISharesParser(Source.RUSSEL3000.value),
        Source.SOXX.value: ISharesParser(Source.SOXX.value),
        Source.SP500.value: SlickChartsParser(Source.SP500.value),
    }

    data_source_url = models.URLField(choices=Source.choices, unique=True)
    status = models.IntegerField(choices=UpdatingStatus.choices,
                                 default=UpdatingStatus.successfully_updated)
    tickers = models.ManyToManyField(Ticker, through='fin.IndexTicker')

    class Meta:
        """
        Index model indexes
        """
        indexes = [
            models.Index(fields=['data_source_url', ]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = self.url_parsers[self.data_source_url]

    def __str__(self):
        return str(dict(Source.choices)[self.data_source_url])

    @transaction.atomic
    def adjust(self, money, options):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = IndexTicker.objects.filter(index=self) \
            .exclude(ticker__country__in=options['skip_countries']) \
            .exclude(ticker__sector__in=options['skip_sectors']) \
            .exclude(ticker__industry__in=options['skip_industries']) \
            .order_by('-weight')
        for ticker in options['skip_tickers']:
            tickers_query = tickers_query.exclude(Q(ticker__stock_exchange=ticker[0], ticker__symbol=ticker[1]))

        # exclude tickers with highest PE ratio

        dataset = tickers_query.values_list('ticker__stock_exchange', 'ticker__symbol', 'ticker__price', 'weight')
        tickers_df = pd.DataFrame(list(dataset),
                                  columns=['ticker__stock_exchange', 'ticker__symbol', 'ticker__price', 'weight'])
        tickers_df['ticker__price'] = tickers_df['ticker__price'].astype(float)
        tickers_df['weight'] = tickers_df['weight'].astype(float)

        coefficient = 100 / tickers_df['weight'].sum()
        tickers_df.iloc[:, 3] *= coefficient

        adjusted_money_amount = money
        step = money * 0.1
        while True:
            tickers_df['amount'] = (tickers_df['weight'] / 100) * adjusted_money_amount \
                                   / tickers_df['ticker__price']
            tickers_df['amount'] = tickers_df['amount'].round()

            tickers_df['cost'] = tickers_df['amount'] * tickers_df['ticker__price']
            if tickers_df[tickers_df['cost'] > (money * 0.1)]['cost'].sum() > money:
                break
            adjusted_money_amount += step

        # tickers_df = tickers_df[tickers_df['cost'] > 200]
        adjusted_money_amount -= step
        tickers_df['amount'] = tickers_df['weight'] / 100 * adjusted_money_amount / tickers_df[
            'ticker__price']
        tickers_df['amount'] = tickers_df['amount'].round()

        tickers_df['cost'] = tickers_df['amount'] * tickers_df['ticker__price']
        tickers_df = tickers_df[tickers_df.cost != 0]

        coefficient = 100 / tickers_df['weight'].sum()
        tickers_df.iloc[:, 3] *= coefficient

        return tickers_df

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert=False, force_update=False, using=None, update_fields=None)
        self.update()

    def threshold_pe_ratio(self, pe_quantile):
        """
        Calculates maximum acceptable pe value for the companies those to be taken to the adjusting
        calculation
        """
        index_pe_list = IndexTicker.objects.filter(index=self, ticker__pe__isnull=False) \
            .values_list('ticker__pe', flat=True) \
            .order_by('ticker__pe')
        if index_pe_list:
            return np.percentile(index_pe_list, pe_quantile)
        return 0

    @transaction.atomic
    def update(self):
        """
        Update tickers prices and their weights
        """
        if self.parser.updatable:
            tickers_parsed_json = self.parser.parse()
            self.update_from_tickers_parsed_json(tickers_parsed_json)

    def update_from_tickers_parsed_json(self, ticker_parsed_json):
        """
        Creates objects for the relation between the current index and tickers JSON
        """
        index_tickers = []
        for ticker_info in ticker_parsed_json:
            stock_exchange = Ticker.DEFAULT_VALUE
            if ticker_info['ticker'].get('stock_exchange'):
                stock_exchange = ticker_info['ticker'].pop('stock_exchange')
            symbol = ticker_info['ticker'].pop('symbol')

            ticker, _ = Ticker.objects \
                .update_or_create(symbol=symbol, stock_exchange=stock_exchange, defaults=ticker_info['ticker'])

            index_ticker = IndexTicker(index=self, ticker=ticker, weight=ticker_info['ticker_weight'])
            index_tickers.append(index_ticker)
        IndexTicker.objects.filter(index=self).delete()
        IndexTicker.objects.bulk_create(index_tickers, batch_size=1000)


class IndexTicker(TimeStampMixin):
    """
    M2M table between Index and Ticker models
    """
    index = models.ForeignKey(Index, on_delete=models.CASCADE, related_name='index')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE, related_name='ticker')
    weight = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=10,
                                 validators=[MinValueValidator(0.000001),
                                             MaxValueValidator(1.000001)])

    class Meta:
        """
        Model indexes
        """
        indexes = [
            models.Index(fields=['index', ]),
            models.Index(fields=['ticker', ]),
            models.Index(fields=['weight', ]),
        ]
