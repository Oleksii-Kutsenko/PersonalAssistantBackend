"""
The Portfolio model serializer and related models serializers
"""
from django.db.models import Sum, F, DecimalField, Min
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from fin.models.portfolio import Portfolio, Account, PortfolioTickers
from fin.models.utils import MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus
from fin.serializers.ticker import TickerSerializer
from fin.serializers.utils import FlattenMixin


class AccountSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Account model
    """
    id = serializers.IntegerField()

    class Meta:
        """
        Serializer meta class
        """
        model = Account
        fields = ('id', 'name', 'currency', 'portfolio', 'value')


class PortfolioTickersSerializer(FlattenMixin, serializers.ModelSerializer):
    """
    Serializer for Ticker model inside Portfolio model
    """
    cost = SerializerMethodField(read_only=True)

    def get_cost(self, obj):
        """
        Returns annotated field - cost
        """
        return obj.cost

    class Meta:
        """
        Serializer meta class
        """
        model = PortfolioTickers
        fields = ('amount', 'cost')
        flatten = [('ticker', TickerSerializer)]
        depth = 1


class PortfolioSerializer(serializers.ModelSerializer):
    """
    Serializer for Portfolio model
    """
    id = serializers.IntegerField(read_only=True)

    class Meta:
        """
        Serializer meta class
        """
        model = Portfolio
        fields = ('id', 'name')


# pylint: disable=no-self-use
class DetailedPortfolioSerializer(PortfolioSerializer):
    accounts = AccountSerializer(many=True, read_only=True)
    industries_breakdown = SerializerMethodField(read_only=True)
    sectors_breakdown = SerializerMethodField(read_only=True)
    status = SerializerMethodField(read_only=True)
    tickers = SerializerMethodField(read_only=True)
    tickers_last_updated = SerializerMethodField(read_only=True)
    total = SerializerMethodField(read_only=True)
    total_accounts = SerializerMethodField(read_only=True)
    total_tickers = SerializerMethodField(read_only=True)

    def get_industries_breakdown(self, obj):
        """
        Returns list of industries and their percentage in the portfolio
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        query = PortfolioTickers.objects.filter(portfolio=obj) \
            .annotate(cost=cost).values('ticker__sector', 'ticker__industry') \
            .annotate(sum_cost=Sum('cost')).order_by('-sum_cost').distinct()
        return query

    def get_sectors_breakdown(self, obj):
        """
        Returns list of sectors and their percentage in the portfolio
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        query = PortfolioTickers.objects.filter(portfolio=obj) \
            .annotate(cost=cost).values('ticker__sector') \
            .annotate(sum_cost=Sum('cost')).order_by('-sum_cost').distinct()
        return query

    def get_status(self, obj):
        """
        Returns Updating Status
        """
        return UpdatingStatus(obj.status).label

    def get_tickers(self, obj):
        """
        Returns portfolio tickers with their cost
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
        cost = Cast(F('amount') * F('ticker__price'), decimal_field)

        portfolio_tickers = PortfolioTickers.objects.filter(portfolio=obj) \
            .annotate(cost=cost).order_by('-cost')
        return PortfolioTickersSerializer(portfolio_tickers, many=True).data

    def get_tickers_last_updated(self, obj):
        """
        Returns portfolio tickers last updated time
        """
        return obj.tickers.aggregate(Min('updated')).get('updated__min') or obj.updated

    def get_total(self, obj):
        """
        Return total property
        """
        return obj.total

    def get_total_accounts(self, obj):
        """
        Return total accounts property
        """
        return obj.total_accounts

    def get_total_tickers(self, obj):
        """
        Return total tickers property
        """
        return obj.total_tickers

    def validate_portfolio_policy(self, value):
        """
        Validate that portfolio_policy field is unchangeable
        """
        if self.instance and self.instance != value:
            raise ValidationError('Portfolio Policy field is unchangeable')
        return value

    class Meta:
        """
        Meta
        """
        model = PortfolioSerializer.Meta.model
        fields = ('accounts', 'industries_breakdown', 'portfolio_policy', 'sectors_breakdown',
                  'status', 'tickers', 'tickers_last_updated', 'total', 'total_accounts',
                  'total_tickers') + PortfolioSerializer.Meta.fields
        depth = 1
