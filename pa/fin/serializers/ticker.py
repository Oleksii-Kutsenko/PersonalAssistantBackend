"""
Serializer for Ticker model in different variants
"""
from datetime import date
from decimal import Decimal
from statistics import mean

from querybuilder.fields import MultiField
from querybuilder.query import Query
from rest_framework import serializers

from fin.models.index import TickerIndexWeight
from fin.models.ticker import Ticker, TickerStatement, Statements
from fin.serializers.utils import FlattenMixin


class DebtToEquityField(MultiField):
    """
    Calculates debt to equity ratio
    """
    def __init__(self, short_debt, long_debt, equity):
        super().__init__()
        self.short_debt = short_debt
        self.long_debt = long_debt
        self.equity = equity
        self.auto_alias = 'debt_to_equity'

    def get_select_sql(self):
        return f'(({self.short_debt}+{self.long_debt})/{self.equity}*100)'


class AssetsToEquityField(MultiField):
    """
    Calculates assets to equity ratio
    """
    def __init__(self, total_assets, equity):
        super().__init__()
        self.total_assets = total_assets
        self.equity = equity
        self.auto_alias = 'assets_to_equity'

    def get_select_sql(self):
        return f'{self.total_assets} / {self.equity}'


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
    fiscal_date_ending_field = TickerStatement.fiscal_date_ending.field.name
    five_years_ago = date(date.today().year - 5, date.today().month, date.today().day)

    annual_earnings_growth = serializers.SerializerMethodField()
    debt = serializers.SerializerMethodField()
    returns_ratios = serializers.SerializerMethodField()

    def get_annual_earnings_growth(self, obj):
        """
        Calculates annual earnings growth
        """
        query = obj.net_income_statements(self.five_years_ago)
        years_ago = query.count() // 4
        if years_ago >= 2:
            first_year_income = sum([statement.value for statement in query[:4]])
            last_year_income = sum([statement.value for statement in query[years_ago * 4 - 4:]])

            return ((first_year_income / last_year_income) ** Decimal(1 / years_ago) - 1) * 100
        return None

    def get_debt(self, obj):
        """
        Calculates equity to debt ratio and assets to debt ratio
        """
        equity_field = 'equity'
        equity_query_id = 'equity_query'
        equity_query = obj.get_debt_statements(Statements.total_shareholder_equity, equity_field)

        short_debt_field = 'short_debt'
        short_debt_query_id = 'short_debt_query'
        short_debt_query = obj.get_debt_statements(Statements.short_term_debt, short_debt_field)

        long_debt_field = 'long_debt'
        long_debt_query_id = 'long_debt_query'
        long_debt_query = obj.get_debt_statements(Statements.total_long_term_debt, long_debt_field)

        total_assets_field = 'total_assets'
        total_assets_query_id = 'total_assets_query'
        total_assets_query = obj.get_debt_statements(Statements.total_assets, total_assets_field)

        query = Query() \
            .from_table({long_debt_query_id: long_debt_query},
                        [self.fiscal_date_ending_field,
                         AssetsToEquityField(total_assets_field, equity_field),
                         DebtToEquityField(short_debt_field, long_debt_field, equity_field)])

        query.with_query(equity_query, equity_query_id)
        query.with_query(short_debt_query, short_debt_query_id)
        query.with_query(total_assets_query, total_assets_query_id)
        query.join(
            equity_query_id,
            condition=f'{long_debt_query_id}.{self.fiscal_date_ending_field} = '
                      f'{equity_query_id}.{self.fiscal_date_ending_field}',
            fields=['equity']
        )
        query.join(
            short_debt_query_id,
            condition=f'{long_debt_query_id}.{self.fiscal_date_ending_field} = '
                      f'{short_debt_query_id}.{self.fiscal_date_ending_field}',
            fields=['short_debt']
        )
        query.join(
            total_assets_query_id,
            condition=f'{long_debt_query_id}.{self.fiscal_date_ending_field} = '
                      f'{total_assets_query_id}.{self.fiscal_date_ending_field}',
            fields=['total_assets']
        )
        query.order_by(self.fiscal_date_ending_field, desc=True).limit(1)

        query = query.select()
        if query:
            return {
                'debt_to_equity': query[0]['debt_to_equity'],
                'assets_to_equity': query[0]['assets_to_equity']
            }
        return None

    def get_returns_ratios(self, obj):
        """
        Calculates ROA and ROE ratios
        """
        roa = None
        roe = None

        net_income = obj.get_returns_statements(Statements.net_income)
        if net_income.count() == 4:

            total_assets = obj.get_returns_statements(Statements.total_assets)
            if total_assets.count() == 4:
                roa = sum([statement.value for statement in net_income]) / \
                      mean([statement.value for statement in total_assets]) \
                      * 100

            equity = obj.get_returns_statements(Statements.total_shareholder_equity)
            if equity.count() == 4:
                roe = sum([statement.value for statement in net_income]) / \
                      mean([statement.value for statement in equity]) \
                      * 100

        return {
            'roa': roa,
            'roe': roe
        }

    class Meta:
        """
        Serializer meta class
        """
        model = Ticker
        fields = ['annual_earnings_growth', 'company_name', 'country', 'debt', 'industry', 'pe',
                  'price', 'returns_ratios', 'sector', 'symbol']
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
