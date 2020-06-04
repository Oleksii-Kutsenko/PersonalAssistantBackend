from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from fin.models.portfolio import Portfolio, Account, PortfolioTickers


class AccountSerializer(serializers.ModelSerializer):
    """
    Serialization class for the Account model
    """
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Account
        fields = '__all__'


class PortfolioTickersSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTickers
        fields = ('ticker', 'amount')
        depth = 1


class PortfolioSerializer(serializers.ModelSerializer):
    accounts = AccountSerializer(many=True)
    tickers = SerializerMethodField()

    def get_tickers(self, obj):
        portfolio_tickers = PortfolioTickers.objects.filter(portfolio=obj)
        return PortfolioTickersSerializer(portfolio_tickers, many=True).data

    class Meta:
        model = Portfolio
        fields = ('accounts', 'tickers')
