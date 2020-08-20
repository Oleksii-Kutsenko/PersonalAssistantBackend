"""
Tests
"""
import factory
from django.urls import reverse
from factory.fuzzy import FuzzyChoice
from faker import Factory
from rest_framework import status

from fin.models.index import Index
from fin.serializers.ticker import AdjustedTickerSerializer
from fin.tests.base import BaseTestCase
from users.models import User

faker = Factory.create()


class IndexFactory(factory.DjangoModelFactory):
    """
    Creates Index object
    """
    class Meta:
        """
        Factory meta class
        """
        model = Index

    data_source_url = FuzzyChoice(Index.Source)


class AdjustedIndexTests(BaseTestCase):
    """
    Tests for index-adjusted endpoint
    """

    def setUp(self) -> None:
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)
        self.index = IndexFactory()

    def test_when_received_right_msg(self):
        """
        Expects correct data when money parameter can be converted to Decimal
        """
        url = reverse('index-adjusted', kwargs={'index_id': self.index.id})
        money = 1000

        response = self.client.get(url, {'money': money})

        options = {
            'skip_industries': [],
            'skip_countries': [],
            'skip_sectors': [],
            'skip_tickers': []
        }
        adjusted_index, _ = self.index.adjust(money, options)
        serialized_index = AdjustedTickerSerializer(adjusted_index, many=True)
        self.assertEqual(response.data.get('tickers'), serialized_index.data)

    def test_when_received_wrong_parameter(self):
        """
        Expects bad request when the money parameter cannot be converted to decimal
        """
        url = reverse('index-adjusted', kwargs={'index_id': self.index.id})
        money = '1000q'

        response = self.client.get(url, {'money': money})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
