"""
PortfolioPolicy Factory
"""
import factory

from fin.models.portfolio.portfolio_policy import PortfolioPolicy
from fin.tests.factories.portfolio import PortfolioFactory


class PortfolioPolicyFactory(factory.DjangoModelFactory):
    """
    Creates PortfolioPolicy objects
    """

    class Meta:
        """
        Meta
        """

        model = PortfolioPolicy

    portfolio = factory.SubFactory(PortfolioFactory)
