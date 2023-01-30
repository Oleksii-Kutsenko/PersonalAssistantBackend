"""
The PortfolioPolicy model serializer and related models serializers
"""
from rest_framework import serializers

from fin.models.portfolio.portfolio_policy import PortfolioPolicy


class PortfolioPolicySerializer(serializers.ModelSerializer):
    """
    Serializer for PortfolioPolicy model
    """

    id = serializers.IntegerField(read_only=True)

    class Meta:
        """
        Meta
        """

        model = PortfolioPolicy
        fields = (
            "asset_to_equity_max_ratio",
            "asset_to_equity_min_ratio",
            "debt_to_equity_max_ratio",
            "id",
            "max_dividend_payout_ratio",
            "minimum_annual_earnings_growth",
            "pe_quantile",
            "portfolio",
        )
