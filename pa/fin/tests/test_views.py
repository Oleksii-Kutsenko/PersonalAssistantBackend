"""
Tests
"""
import factory
from django.urls import reverse
from factory.fuzzy import FuzzyChoice
from faker import Factory
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APITestCase, APIRequestFactory

from fin.models import Goal, Index
from fin.serializers import GoalSerializer, AdjustedTickerSerializer

faker = Factory.create()


class GoalFactory(factory.DjangoModelFactory):
    class Meta:
        model = Goal

    name = faker.pystr(min_chars=None, max_chars=50)
    coefficient = faker.pyfloat(left_digits=None, right_digits=2, positive=True,
                                min_value=0, max_value=1)
    target_money_amount = faker.pyint(min_value=101)
    current_money_amount = faker.pyint(max_value=100)
    level = faker.pyint()


class IndexFactory(factory.DjangoModelFactory):
    class Meta:
        model = Index

    data_source_url = FuzzyChoice(Index.Source)


class GoalsTests(APITestCase):
    """
    Tests for the goals API
    """

    def setUp(self):
        """
        Creating goal objects
        """
        self.test_objects = []
        for _ in range(0, 3):
            self.test_objects.append(GoalFactory())

    def test_get_all_goals(self):
        """
        Tests GET request on goal-list
        """
        url = reverse('goal-list')
        response = self.client.get(url)
        serializer = GoalSerializer(Goal.objects.all(), many=True,
                                    context={'request': Request(APIRequestFactory().get(url))})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 3)
        self.assertEqual(response.data.get('results'), serializer.data)

    def test_get_valid_single_goal(self):
        """
        Tests GET request on goal-detail
        """
        url = reverse('goal-detail', kwargs={'pk': self.test_objects[0].pk})
        response = self.client.get(url)
        serializer = GoalSerializer(Goal.objects.get(pk=self.test_objects[0].pk),
                                    context={'request': Request(APIRequestFactory().get(url))})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_get_invalid_single_goal(self):
        """
        Tests invalid GET request on goal-detail
        """
        url = reverse('goal-detail', kwargs={'pk': -1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_valid_goal(self):
        """
        Tests POST request on goal-list
        """
        url = reverse('goal-list')
        response = self.client.post(url, {"name": "test_name",
                                          "coefficient": "1.00",
                                          "current_money_amount": "0.00",
                                          "target_money_amount": "10000.00",
                                          "level": "1"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid_goal(self):
        """
        Tests invalid POST request on goal-list
        """
        json_data = {"name": "test_name",
                     "coefficient": "1.00",
                     "current_money_amount": "10001.00",
                     "target_money_amount": "10000.00",
                     "level": "1"}

        url = reverse('goal-list')
        response = self.client.post(url, json_data)
        serializer = GoalSerializer(data=json_data)
        serializer.is_valid()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('current_money_amount')[0],
                         serializer.errors.get('current_money_amount')[0])

    def test_valid_update_goal(self):
        """
        Tests valid PUT request
        """
        url = reverse('goal-detail', kwargs={'pk': self.test_objects[0].pk})
        response = self.client.put(url, {"name": "Updated",
                                         "coefficient": "1.00",
                                         "current_money_amount": "10.00",
                                         "target_money_amount": "10050.00",
                                         "level": "2"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_update_goal(self):
        """
        Tests invalid PUT request
        """
        url = reverse('goal-detail', kwargs={'pk': self.test_objects[0].pk})
        response = self.client.put(url, {"name": "",
                                         "coefficient": "-1.00",
                                         "current_money_amount": "-10.00",
                                         "target_money_amount": "-9.00"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_goal_level_up(self):
        """
        Tests automatic level up
        """
        test_object = self.test_objects[1]
        url = reverse('goal-detail', kwargs={'pk': test_object.pk})

        response = self.client.put(url, {"name": test_object.name,
                                         "coefficient": test_object.coefficient,
                                         "current_money_amount": test_object.target_money_amount,
                                         "target_money_amount": test_object.target_money_amount,
                                         "level": test_object.level})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('level'), test_object.level + 1)

    def test_valid_delete_goal(self):
        """
        Tests valid DELETE request
        """
        test_object = self.test_objects[2]
        url = reverse('goal-detail', kwargs={'pk': test_object.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_invalid_delete_goal(self):
        """
        Tests invalid DELETE request
        """
        url = reverse('goal-detail', kwargs={'pk': -1})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AdjustedIndexTests(APITestCase):
    """
    Tests for index-adjusted endpoint
    """

    def setUp(self) -> None:
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
        adjusted_index, summary_cost = self.index.adjust(money, options)
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
