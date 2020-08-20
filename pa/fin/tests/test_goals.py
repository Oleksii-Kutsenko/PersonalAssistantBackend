import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from fin.models.models import Goal
from fin.serializers.serializers import GoalSerializer
from fin.tests.base import BaseTestCase
from fin.tests.test_index import faker
from users.models import User


class GoalsTests(BaseTestCase):
    """
    Tests for the goals API
    """

    def setUp(self):
        """
        Creating goal objects
        """
        self.user = User.objects.create(username='test_user', email='test_user@gmail.com')
        self.login(self.user)
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


class GoalFactory(factory.DjangoModelFactory):
    class Meta:
        model = Goal

    name = faker.pystr(min_chars=None, max_chars=50)
    coefficient = faker.pyfloat(left_digits=None, right_digits=2, positive=True,
                                min_value=0, max_value=1)
    target_money_amount = faker.pyint(min_value=101)
    current_money_amount = faker.pyint(max_value=100)
    level = faker.pyint()
