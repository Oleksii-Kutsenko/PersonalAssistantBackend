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

    source = models.OneToOneField('Source', on_delete=models.CASCADE)
    status = models.IntegerField(choices=UpdatingStatus.choices, default=UpdatingStatus.successfully_updated)
    tickers = models.ManyToManyField(Ticker, through='fin.IndexTicker')

    class Meta:
        """
        Index model indexes
        """
        indexes = [
            models.Index(fields=['source', ]),
        ]

    def __str__(self):
        return self.source.name

    @transaction.atomic
    def adjust(self, invested_money: float, extra_money: float, options):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = IndexTicker.objects.filter(index=self) \
            .exclude(ticker__id__in=options['skip_tickers']) \
            .exclude(ticker__stock_exchange__available=False) \
            .exclude(ticker__country__in=options['skip_countries']) \
            .exclude(ticker__sector__in=options['skip_sectors']) \
            .exclude(ticker__industry__in=options['skip_industries']) \
            .exclude(ticker__price__gt=extra_money) \
            .order_by('-weight')

        if tickers_query.count() == 0:
            raise Exception('Not enough data for adjusting')

        dataset = list(tickers_query.values_list('ticker__id', 'ticker__price', 'weight'))
        tickers_df = pd.DataFrame(dataset, columns=['id', 'price', 'weight'])

        tickers_df.id = tickers_df.id.astype(object)
        tickers_df.price = tickers_df.price.astype(float)
        tickers_df.weight = tickers_df.weight.astype(float)

        coefficient = 1 / tickers_df.weight.sum()
        tickers_df.iloc[:, 2] *= coefficient

        step = 100
        max_tickers_cost = invested_money + extra_money
        adjusted_money_amount = invested_money + extra_money
        while True:
            adjusted_money_amount += step
            self.evaluate_dataframe(adjusted_money_amount, tickers_df)

            if tickers_df.cost.sum() > max_tickers_cost:
                adjusted_money_amount -= step
                self.evaluate_dataframe(adjusted_money_amount, tickers_df)

                break

        tickers_df = tickers_df[tickers_df.cost != 0]
        return tickers_df

    @staticmethod
    def evaluate_dataframe(money, tickers_df):
        """
        Adjust the dataframe by given amount of money
        """
        tickers_df['amount'] = tickers_df.weight * money / tickers_df.price
        tickers_df.amount = tickers_df.amount.round()
        tickers_df['cost'] = tickers_df.amount * tickers_df.price

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
            self.update_from_parsed_index_tickers(parsed_index_tickers)

    def update_from_parsed_index_tickers(self, parsed_index_tickers):
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
