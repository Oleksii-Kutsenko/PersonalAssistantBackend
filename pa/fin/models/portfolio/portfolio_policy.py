"""
Portfolio Policy model
"""
from django.db import models

from fin.models.portfolio import Portfolio
from fin.models.utils import TimeStampMixin, MAX_DIGITS, DECIMAL_PLACES


class PortfolioPolicy(TimeStampMixin):
    """
    The model that implements portfolio policy (used for the adjusting functionality)
    """
    asset_to_equity_max_ratio = models.DecimalField(max_digits=MAX_DIGITS,
                                                    decimal_places=DECIMAL_PLACES, default=0)
    asset_to_equity_min_ratio = models.DecimalField(max_digits=MAX_DIGITS,
                                                    decimal_places=DECIMAL_PLACES, default=0)
    debt_to_equity_max_ratio = models.DecimalField(max_digits=MAX_DIGITS,
                                                   decimal_places=DECIMAL_PLACES, default=0)
    max_dividend_payout_ratio = models.DecimalField(max_digits=MAX_DIGITS,
                                                    decimal_places=DECIMAL_PLACES, default=0)
    minimum_annual_earnings_growth = models.DecimalField(max_digits=MAX_DIGITS,
                                                         decimal_places=DECIMAL_PLACES, default=0)
    pe_quantile = models.IntegerField(default=50)
    portfolio = models.OneToOneField(Portfolio, on_delete=models.CASCADE,
                                     related_name='portfolio_policy')
