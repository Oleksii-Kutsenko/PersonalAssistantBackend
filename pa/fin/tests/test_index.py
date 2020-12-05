"""
Tests
"""
from random import choice
from time import sleep

from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from fin.models.index import Index
from fin.models.index.parsers import Source
from fin.tasks.update_tickers_statements import update_model_tickers_statements_task, LOCKED
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

    def test_index_creation(self):
        """
        Tests that after index creation runs task for updating the index tickers
        """
        url = reverse('index-list')
        index = IndexFactory.build()

        response = self.client.post(url, {'data_source_url': index.data_source_url})
        task_args = (Index.__name__, response.data.get('id'))
        task = update_model_tickers_statements_task.apply(args=task_args)
        while not task.ready():
            sleep(0.1)

        self.assertEqual(task.result, LOCKED)

    def test_the_right_serialization_class_used(self):
        """
        Tests if viewset use right serializer
        """
        index = IndexFactory()
        index_list_url = reverse('index-list')
        detailed_index_url = reverse('index-detail', kwargs={'pk': index.id})
        list_response = self.client.get(index_list_url)
        detailed_response = self.client.get(detailed_index_url)

        assert 'industries_breakdown' in detailed_response.data.keys()
        assert 'sectors_breakdown' in detailed_response.data.keys()

        assert len(list_response.data['results'][0]) == 6
