from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from fin.models.portfolio import Portfolio, Account, PortfolioTickers
from fin.models.utils import MAX_DIGITS, DECIMAL_PLACES
from fin.serializers.index import TickerSerializer
from fin.serializers.utils import FlattenMixin


class AccountSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Account model
    """
    id = serializers.IntegerField()

    class Meta:
        model = Account
        fields = ('id', 'name', 'currency', 'portfolio', 'value')


class PortfolioTickersSerializer(FlattenMixin, serializers.ModelSerializer):
    cost = SerializerMethodField(read_only=True)

    def get_cost(self, obj):
        return obj.cost

    class Meta:
        model = PortfolioTickers
        fields = ('amount', 'cost')
        flatten = [('ticker', TickerSerializer)]
        depth = 1


class PortfolioSerializer(serializers.ModelSerializer):
    accounts = AccountSerializer(many=True, read_only=True)
    id = serializers.IntegerField(read_only=True)
    industries_breakdown = SerializerMethodField(read_only=True)
    sectors_breakdown = SerializerMethodField(read_only=True)
    tickers = SerializerMethodField(read_only=True)
    total = SerializerMethodField(read_only=True)
    total_accounts = SerializerMethodField(read_only=True)
    total_tickers = SerializerMethodField(read_only=True)

    def get_industries_breakdown(self, obj):
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        query = PortfolioTickers.objects.filter(portfolio=obj) \
            .annotate(cost=cost).values('ticker__sector', 'ticker__industry') \
            .annotate(sum_cost=Sum('cost')).order_by('-sum_cost').distinct()
        return query

    def get_sectors_breakdown(self, obj):
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        query = PortfolioTickers.objects.filter(portfolio=obj) \
            .annotate(cost=cost).values('ticker__sector') \
            .annotate(sum_cost=Sum('cost')).order_by('-sum_cost').distinct()
        return query

    def get_tickers(self, obj):
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        portfolio_tickers = PortfolioTickers.objects.filter(portfolio=obj).annotate(cost=cost).order_by('-cost')
        return PortfolioTickersSerializer(portfolio_tickers, many=True).data

    def get_total(self, obj):
        return self.get_total_tickers(obj) + self.get_total_accounts(obj)

    def get_total_accounts(self, obj):
        accounts_sum = Account.objects.filter(portfolio=obj).aggregate(Sum('value')).get('value__sum')
        return accounts_sum or 0

    def get_total_tickers(self, obj):
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)
        query = PortfolioTickers.objects.filter(portfolio=obj).annotate(cost=cost)
        tickers_sum = query.aggregate(Sum('cost')).get('cost__sum')
        return tickers_sum

    class Meta:
        model = Portfolio
        fields = ('id', 'accounts', 'tickers', 'name', 'total_accounts', 'total_tickers', 'total', 'sectors_breakdown',
                  'industries_breakdown')
