"""
Classes that helps operate with indexes and tickers
"""

import numpy as np
import pandas as pd
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction

from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, UpdatingStatus


class Index(TimeStampMixin):
    """
    Index model
    """

    source = models.ForeignKey('Source', on_delete=models.CASCADE)
    status = models.IntegerField(choices=UpdatingStatus.choices,
                                 default=UpdatingStatus.successfully_updated)
    tickers = models.ManyToManyField(Ticker, through='fin.IndexTicker')

    class Meta:
        """
        Index model indexes
        """
        indexes = [
            models.Index(fields=['source', ]),
        ]

    @transaction.atomic
    def adjust(self, money, options):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = IndexTicker.objects.filter(index=self) \
            .exclude(ticker__id__in=options['skip_tickers']) \
            .exclude(ticker__stock_exchange__available=False) \
            .exclude(ticker__country__in=options['skip_countries']) \
            .exclude(ticker__sector__in=options['skip_sectors']) \
            .exclude(ticker__industry__in=options['skip_industries']) \
            .order_by('-weight')

        if tickers_query.count() == 0:
            raise Exception('Not enough data for adjusting')

        dataset = tickers_query.values_list('ticker__id', 'ticker__symbol', 'ticker__price', 'weight')
        tickers_df = pd.DataFrame(list(dataset),
                                  columns=['ticker__id', 'ticker__symbol', 'ticker__price', 'weight'])
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
        if self.source.updatable:
            parsed_index_tickers = self.source.parser.parse()
            self.update_from_parsed_index_ticker(parsed_index_tickers)

    def update_from_parsed_index_ticker(self, parsed_index_tickers):
        """
        Creates objects for the relation between the current index and tickers JSON
        """
        index_tickers = []
        for parsed_index_ticker in parsed_index_tickers:
            ticker = parsed_index_ticker.ticker.get_ticker()

            index_ticker = IndexTicker(index=self, raw_data=parsed_index_ticker.raw_data, ticker=ticker,
                                       weight=parsed_index_ticker.weight)
            index_tickers.append(index_ticker)

        IndexTicker.objects.filter(index=self).delete()
        IndexTicker.objects.bulk_create(index_tickers, batch_size=300)


class IndexTicker(TimeStampMixin):
    """
    M2M table between Index and Ticker models
    """
    index = models.ForeignKey(Index, on_delete=models.CASCADE, related_name='index')
    raw_data = models.JSONField(default=dict)
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE, related_name='ticker')
    weight = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=10,
                                 validators=[MinValueValidator(0.000001),
                                             MaxValueValidator(1.000001)])

    def __str__(self):
        return f'{self.index}.{self.ticker}'

    class Meta:
        """
        Model indexes
        """
        constraints = [
            models.UniqueConstraint(fields=('index_id', 'ticker_id'), name='index_ticker_unique')
        ]
        indexes = [
            models.Index(fields=['index', ]),
            models.Index(fields=['ticker', ]),
            models.Index(fields=['weight', ]),
        ]
