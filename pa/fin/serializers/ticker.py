"""
Serializer for Ticker model in different variants
"""
from rest_framework import serializers

from fin.models.index import TickerIndexWeight
from fin.models.ticker import Ticker
from fin.serializers.utils import FlattenMixin


class TickerSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Ticker model
    """

    class Meta:
        """
        Serializer meta class
        """
        model = Ticker
        fields = ['company_name', 'symbol', 'price', 'industry', 'sector', 'country',
                  'ticker_multipliers']
        depth = 1


# pylint: disable=no-self-use
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
