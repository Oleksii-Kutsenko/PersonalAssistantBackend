"""
Serializers
"""
from rest_framework import serializers

from .models import Account, Index, Ticker, Goal


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Account model
    """
    id = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta"""
        model = Account
        fields = '__all__'


class TickerSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Ticker model
    """

    class Meta:
        """Meta"""
        model = Ticker
        fields = ['company', 'symbol', 'weight', 'price', 'industry', 'sector', 'country']


class AdjustedTickerSerializer(TickerSerializer):
    amount = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()

    def get_amount(self, obj):
        return obj.amount

    def get_cost(self, obj):
        return obj.cost

    class Meta:
        model = Ticker
        fields = ['company', 'symbol', 'weight', 'price', 'country', 'sector', 'industry', 'amount',
                  'cost']


class IndexSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Index model
    """
    id = serializers.IntegerField(read_only=True)
    tickers = serializers.SerializerMethodField()

    class Meta:
        """Meta"""
        model = Index
        fields = '__all__'

    def get_tickers(self, instance):
        return TickerSerializer(instance.tickers.order_by('-weight').all(), many=True).data


class GoalSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Goal model
    """
    id = serializers.IntegerField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(GoalSerializer, self).__init__(*args, **kwargs)
        self.error_messages['current_money_amount'] = \
            'Target money amount must be greater or equals to the current money amount'

    def validate(self, attrs):
        data = super().validate(attrs)

        if data['current_money_amount'] > data['target_money_amount']:
            raise serializers.ValidationError({'current_money_amount':
                                                   self.error_messages['current_money_amount']})

        return data

    class Meta:
        """Meta"""
        model = Goal
        fields = '__all__'
