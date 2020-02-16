"""
Tests
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APITestCase, APIRequestFactory

from fin.models import Goal
from fin.serializers import GoalSerializer


class GoalsTest(APITestCase):
    """
    Tests for the goals API
    """

    def setUp(self):
        """
        Set Up
        """
        Goal.objects.create(name='First',
                            coefficient=0.1,
                            current_money_amount=0,
                            target_money_amount=1000).save()
        Goal.objects.create(name='Second',
                            coefficient=0.5,
                            current_money_amount=0,
                            target_money_amount=1000).save()
        Goal.objects.create(name='Third',
                            coefficient=1,
                            current_money_amount=0,
                            target_money_amount=1000).save()
        self.test_objects = Goal.objects.all()

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
                                          "target_money_amount": "10000.00"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid_goal(self):
        """
        Tests invalid POST request on goal-list
        """
        json_data = {"name": "test_name",
                     "coefficient": "1.00",
                     "current_money_amount": "10001.00",
                     "target_money_amount": "10000.00"}

        url = reverse('goal-list')
        response = self.client.post(url, json_data)
        serializer = GoalSerializer(data=json_data)
        serializer.is_valid()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get('current_money_amount')[0],
                         serializer.errors.get('current_money_amount')[0])

    def test_valid_update_goal(self):
        """
        Tests valid PUT request
        """
        url = reverse('goal-detail', kwargs={'pk': self.test_objects[0].pk})
        response = self.client.put(url, {"name": "Updated",
                                         "coefficient": "1.00",
                                         "current_money_amount": "10.00",
                                         "target_money_amount": "10050.00"})
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

        self.client.put(url, {"name": test_object.name,
                              "coefficient": test_object.coefficient,
                              "current_money_amount": test_object.target_money_amount,
                              "target_money_amount": test_object.target_money_amount})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        test_object.current_money_amount = test_object.target_money_amount
        test_object.save()
        serializer = GoalSerializer(test_object,
                                    context={'request': Request(APIRequestFactory().get(url))})
        self.assertEqual(response.data.get('target_money_amount'),
                         serializer.data.get('target_money_amount'))

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
