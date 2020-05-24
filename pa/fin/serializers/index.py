from rest_framework import serializers

from fin.models.index import Ticker, TickerIndexWeight, Index


class TickerSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Ticker model
    """

    class Meta:
        model = Ticker
        fields = ['company_name', 'symbol', 'price', 'industry', 'sector', 'country']


class TickerIndexWeightSerializer(serializers.ModelSerializer):
    ticker = TickerSerializer()

    class Meta:
        model = TickerIndexWeight
        fields = ('ticker', 'weight')


class IndexSerializer(serializers.ModelSerializer):
    """
    Serialization class for the relation between indexes and tickers
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return dict(Index.Source.choices)[obj.data_source_url]

    class Meta:
        model = Index
        fields = ('id', 'data_source_url', 'name')


class AdjustedTickerSerializer(TickerSerializer):
    amount = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()
    ticker = TickerSerializer()

    def get_amount(self, obj):
        return obj.amount

    def get_cost(self, obj):
        return obj.cost

    class Meta:
        model = TickerIndexWeight
        fields = ['ticker', 'amount', 'cost']
