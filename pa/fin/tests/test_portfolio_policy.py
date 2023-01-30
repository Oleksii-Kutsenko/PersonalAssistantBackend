"""
PortfolioPolicy Tests
"""
from django.urls import reverse

from fin.tests.base import BaseTestCase
from fin.tests.factories.portfolio_policy import PortfolioPolicyFactory
from users.models import User


class PortfolioPolicyTests(BaseTestCase):
    """
    Tests for PortfolioPolicy class and related functionality
    """

    def setUp(self) -> None:
        self.user = User.objects.create(
            username="test_user", email="test_user@gmail.com"
        )
        self.login(self.user)

    def test_portfolio_policy(self):
        """
        Tests that portfolio policies viewable only for the owner
        """
        portfolio_policy = PortfolioPolicyFactory.build()
        portfolio_policy.portfolio.user = self.user
        portfolio_policy.portfolio.save()
        portfolio_policy.save()

        url = reverse("portfolio-policies-list")
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

        new_user = User.objects.create(
            username="test_user_2", email="test_user_2@gmail.com"
        )
        self.login(new_user)
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 0)
