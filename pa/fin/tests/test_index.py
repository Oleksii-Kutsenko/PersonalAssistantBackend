"""
Tests
"""
from random import choice

from django.urls import reverse
from rest_framework import status
from rest_framework.status import HTTP_200_OK

from fin.models.index import Index
from fin.models.index.parsers import Source
from fin.serializers.ticker import AdjustedTickerSerializer
from fin.tests.base import BaseTestCase
from fin.tests.factories.index import IndexFactory
from users.models import User


class IndexTests(BaseTestCase):
    """
    Tests for index amount
    """

    def setUp(self) -> None:
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)
        self.index = IndexFactory()

    def test_import_index_from_csv(self):
        """
        Tests
        """
        url = reverse('admin:import-csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTP_200_OK)

        index_choice = choice(response.context['form'].fields['index'].choices)[0]
        with open(f'fin/tests/files/{Source(index_choice).label}.csv') as file:
            response = self.client.post(url, {'index': index_choice, 'csv_file': file}, follow=True)
            self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(Index.objects.filter(data_source_url=index_choice).count(), 1)

    def test_the_right_serialization_class_used(self):
        """
        Tests if viewset use right serializer
        """
        index_list_url = reverse('index-list')
        detailed_index_url = reverse('index-detail', kwargs={'pk': self.index.id})
        list_response = self.client.get(index_list_url)
        detailed_response = self.client.get(detailed_index_url)

        assert 'industries_breakdown' in detailed_response.data.keys()
        assert 'sectors_breakdown' in detailed_response.data.keys()

        assert len(list_response.data['results'][0]) == 6


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
