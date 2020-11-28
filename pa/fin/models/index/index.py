"""
Classes that helps operate with indexes and tickers
"""
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import DecimalField, Sum, F
from django.db.models.functions import Cast, Coalesce

from fin.models.index.parsers import SlickChartsParser, ISharesParser, Source, InvescoCSVParser
from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus


class Index(TimeStampMixin):
    """
    Index model
    """

    url_parsers = {
        Source.IHI.value: ISharesParser(Source.IHI.value),
        Source.NASDAQ100.value: SlickChartsParser(Source.NASDAQ100.value),
        Source.PBW.value: InvescoCSVParser(),
        Source.RUSSEL3000.value: ISharesParser(Source.RUSSEL3000.value),
        Source.SOXX.value: ISharesParser(Source.SOXX.value),
        Source.SP500.value: SlickChartsParser(Source.SP500.value),
    }

    data_source_url = models.URLField(choices=Source.choices, unique=True)
    status = models.IntegerField(choices=UpdatingStatus.choices,
                                 default=UpdatingStatus.successfully_updated)
    tickers = models.ManyToManyField(Ticker, through='TickerIndexWeight')

    class Meta:
        """
        Index model indexes
        """
        indexes = [
            models.Index(fields=['data_source_url', ]),
        ]

    @transaction.atomic
    def adjust(self, money, options, step=None):
        """
        Calculate index adjusted by the amount of money
        """

        tickers_query = TickerIndexWeight.objects.filter(index=self) \
            .exclude(ticker__country__in=options['skip_countries']) \
            .exclude(ticker__sector__in=options['skip_sectors']) \
            .exclude(ticker__industry__in=options['skip_industries']) \
            .exclude(ticker__symbol__in=options['skip_tickers']) \
            .order_by('-weight')

        # adjust sum of weights to 100%
        hundred_percent = Decimal(100)
        tickers_weight = tickers_query.aggregate(Sum('weight')).get('weight__sum')
        coefficient = hundred_percent / tickers_weight

        for ticker in tickers_query:
            ticker.weight *= coefficient

        # compute amount
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        integer_field = models.IntegerField()
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        adjusted_money_amount = Decimal(money)
        # experimentally established value
        step = step or Decimal(money) * Decimal(4)

        def amount(money_amount):
            return Cast(F('weight') / 100 * money_amount / F('ticker__price'), integer_field)

        summary_cost = 0
        while summary_cost < money:
            adjusted_money_amount += step
            tickers_query = tickers_query.annotate(amount=amount(adjusted_money_amount), cost=cost)

            summary_cost = tickers_query \
                .aggregate(summary_cost=Coalesce(Sum('cost'), 0)).get('summary_cost')

        adjusted_money_amount -= step
        tickers_query = tickers_query \
            .annotate(amount=amount(adjusted_money_amount), cost=cost)
        summary_cost = tickers_query.aggregate(Sum('cost')).get('cost__sum')

        if len(tickers_query) == 0:
            return tickers_query, 0

        # adjust sum of weights to 100%
        tickers_query = tickers_query.filter(amount__gt=0)
        tickers_weight = tickers_query.aggregate(Sum('weight')).get('weight__sum')
        coefficient = hundred_percent / tickers_weight

        for ticker in tickers_query:
            ticker.weight *= coefficient

        return tickers_query, summary_cost

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert=False, force_update=False, using=None, update_fields=None)
        self.update()

    @transaction.atomic
    def update(self):
        """
        Update tickers prices and their weights
        :return: None
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
            symbol = ticker_info['ticker'].pop('symbol')
            ticker, _ = Ticker.objects \
                .update_or_create(symbol=symbol, defaults=ticker_info['ticker'])

            index_ticker = TickerIndexWeight(index=self, ticker=ticker,
                                             weight=ticker_info['ticker_weight'])
            index_tickers.append(index_ticker)
        TickerIndexWeight.objects.filter(index=self).delete()
        TickerIndexWeight.objects.bulk_create(index_tickers)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = self.url_parsers[self.data_source_url]

    def __str__(self):
        return str(dict(Source.choices)[self.data_source_url])


class TickerIndexWeight(TimeStampMixin):
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
