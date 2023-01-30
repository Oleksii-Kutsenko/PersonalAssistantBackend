"""
PortfolioTicker model and related stuff
"""
from django.db import models
from django.db.models import ForeignKey, CASCADE, IntegerField

from fin.models.ticker import Ticker
from fin.models.utils import TimeStampMixin


class PortfolioTicker(TimeStampMixin):
    """
    Associated table for M2M relation between Portfolio model and Ticker model
    """

    portfolio = ForeignKey("Portfolio", on_delete=CASCADE, related_name="portfolio")
    ticker = ForeignKey(Ticker, on_delete=CASCADE, related_name="portfolio_ticker")
    amount = IntegerField()

    class Meta:
        """
        Model meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["portfolio_id", "ticker_id"],
                name="portfolio_id_ticker_id_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=[
                    "portfolio",
                ]
            ),
            models.Index(
                fields=[
                    "ticker",
                ]
            ),
        ]
