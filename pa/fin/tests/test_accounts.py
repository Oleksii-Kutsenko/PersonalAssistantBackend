"""
Tests for Account model and related functionality
"""
from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from fin.tests.base import BaseTestCase
from fin.tests.factories.account import AccountFactory
from users.models import User


class AccountTests(BaseTestCase):
    """
    Tests for Account class
    """

    def setUp(self) -> None:
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)
        self.test_objects = []
        for _ in range(0, 3):
            self.test_objects.append(AccountFactory())

    def test_get_all_accounts(self):
        """
        Tests GET request of accounts list
        """
        url = reverse('account-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()['count'], 3)
