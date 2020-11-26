"""
The PortfolioPolicy model serializer and related models serializers
"""
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from fin.models.portfolio.portfolio_policy import PortfolioPolicy


class PortfolioPolicySerializer(serializers.ModelSerializer):
    """
    Serializer for PortfolioPolicy model
    """
    def validate_portfolio(self, value):
        """
        Validate that portfolio field is unchangeable
        """
        if self.instance and self.instance != value:
            raise ValidationError('Portfolio field is unchangeable')
        return value

    class Meta:
        """
        Meta
        """
        model = PortfolioPolicy
        fields = ('asset_to_equity_max_ratio', 'asset_to_equity_min_ratio',
                  'debt_to_equity_max_ratio', 'max_dividend_payout_ratio',
                  'minimum_annual_earnings_growth', 'pe_quantile', 'portfolio')
