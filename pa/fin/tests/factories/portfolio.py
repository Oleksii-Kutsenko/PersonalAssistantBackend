"""
Portfolio Factory
"""
import factory

from fin.models.portfolio import Portfolio
from fin.tests.factories.user import UserFactory


class PortfolioFactory(factory.DjangoModelFactory):
    """
    Creates Portfolio objects
    """

    class Meta:
        """
        Meta
        """

        model = Portfolio

    user = factory.SubFactory(UserFactory)
