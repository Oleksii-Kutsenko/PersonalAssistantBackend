"""
Serializer for Ticker model in different variants
"""
from datetime import date
from statistics import mean

import numpy as np
from dateutil.relativedelta import relativedelta
from querybuilder.fields import MultiField
from querybuilder.query import Query
from rest_framework import serializers
from sklearn.linear_model import LinearRegression

from fin.models.ticker import Ticker, TickerStatement, Statements


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
    almost_six_years_ago = date.today() - relativedelta(years=5, months=11)

    annual_earnings_growth = serializers.SerializerMethodField()
    debt = serializers.SerializerMethodField()
    shares_dilution = serializers.SerializerMethodField()
    returns_ratios = serializers.SerializerMethodField()

    def get_annual_earnings_growth(self, obj):
        """
        Calculates annual earnings growth
        """
        yearly_earnings = []
        quarter = 4
        query = obj.net_income_statements(self.almost_six_years_ago)
        if extra_statements := query.count() - 23 > 0:
            query = query[extra_statements:]
        counter = query.count()

        if counter < quarter:
            return None

        while counter >= quarter:
            yearly_earnings.append(query[counter - 1].value +
                                   query[counter - 2].value +
                                   query[counter - 3].value +
                                   query[counter - 4].value)
            counter -= 1

        yearly_earnings = np.array(yearly_earnings)
        time_points = np.array(list(range(yearly_earnings.shape[0]))).reshape((-1, 1))
        annual_earnings_line_model = LinearRegression()
        annual_earnings_line_model.fit(time_points, yearly_earnings)

        average_earnings = float(np.mean(yearly_earnings))
        result_value = round((annual_earnings_line_model.coef_[0] * 4 / average_earnings) * 100, 2)
        return result_value

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

        # pylint: disable=broad-except
        try:
            query = query.select()
            if query:
                return {
                    'debt_to_equity': round(query[0]['debt_to_equity'], 2),
                    'assets_to_equity': round(query[0]['assets_to_equity'], 2)
                }
            return {
                'debt_to_equity': None,
                'assets_to_equity': None,
            }
        except Exception:
            return {
                'debt_to_equity': None,
                'assets_to_equity': None,
            }
        # pylint: enable=broad-except

    def get_shares_dilution(self, obj):
        """
        Return shares dilution rate
        """
        current_shares_amount = (
            obj.ticker_statements
                .filter(name=Statements.outstanding_shares)
                .order_by('-fiscal_date_ending')
                .first()
        )

        last_year_shares_amount = (
            obj.ticker_statements
                .filter(name=Statements.outstanding_shares,
                        fiscal_date_ending__lte=date.today() - relativedelta(years=1),
                        fiscal_date_ending__gte=date.today() - relativedelta(years=2))
                .order_by('-fiscal_date_ending')
                .first()
        )

        if current_shares_amount and last_year_shares_amount:
            shares_dilution_rate = current_shares_amount.value / last_year_shares_amount.value
            return round((shares_dilution_rate - 1) * 100, 2)
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
                roa = round(sum([statement.value for statement in net_income]) / \
                            mean([statement.value for statement in total_assets]) \
                            * 100, 2)

            equity = obj.get_returns_statements(Statements.total_shareholder_equity)
            if equity.count() == 4:
                roe = round(sum([statement.value for statement in net_income]) / \
                            mean([statement.value for statement in equity]) \
                            * 100, 2)

        if roa is None and roe is None:
            return None
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
                  'price', 'returns_ratios', 'sector', 'shares_dilution', 'stock_exchange', 'symbol', 'updated']
        depth = 1
