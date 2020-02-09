from rest_framework import serializers

from .models import Account, Index, Ticker


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Account
        fields = '__all__'


class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = ['name', 'weight', 'price']


class IndexSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    tickers = TickerSerializer(many=True, read_only=True)
    tickers_last_updated = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Index
        fields = '__all__'
