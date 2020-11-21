"""
Account Factory
"""
import factory

from fin.models.portfolio import Account
from fin.tests.factories.portfolio import PortfolioFactory


class AccountFactory(factory.DjangoModelFactory):
    """
    Creates Account objects
    """

    class Meta:
        """
        Meta
        """
        model = Account

    portfolio = factory.SubFactory(PortfolioFactory)
