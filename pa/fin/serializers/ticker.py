"""
Serializer for Ticker model in different variants
"""
from datetime import date

from rest_framework import serializers

from fin.models.index import TickerIndexWeight
from fin.models.ticker import Ticker, TickerStatement
from fin.serializers.utils import FlattenMixin


# pylint: disable=no-self-use
class TickerStatementSerializer(serializers.ModelSerializer):
    """
    Serialization class for the TickerStatement model
    """
    class Meta:
        """
        Serializer meta class
        """
        model = TickerStatement
        fields = ['name', 'fiscal_date_ending', 'value']


class TickerSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Ticker model
    """
    ticker_statements = serializers.SerializerMethodField()

    def get_ticker_statements(self, obj):
        """
        Returns ticker statements in a range of 5 years
        """
        today = date.today()
        five_years_ago = date(today.year - 5, today.month, today.day)
        query = obj.ticker_statements.filter(fiscal_date_ending__gte=five_years_ago)
        return TickerStatementSerializer(query, many=True).data

    class Meta:
        """
        Serializer meta class
        """
        model = Ticker
        fields = ['company_name', 'symbol', 'price', 'industry', 'sector', 'country',
                  'ticker_statements']
        depth = 1


class AdjustedTickerSerializer(FlattenMixin, serializers.ModelSerializer):
    """
    Serializer for ticker model that returns from the adjust function
    """
    amount = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()

    def get_amount(self, obj):
        """
        Returns annotated field - the amount
        """
        return obj.amount

    def get_cost(self, obj):
        """
        Returns annotated field - the cost
        """
        return obj.cost

    class Meta:
        """
        Serializer meta class
        """
        model = TickerIndexWeight
        fields = ('amount', 'cost', 'weight')
        flatten = [('ticker', TickerSerializer)]
