"""
Test utils
"""
from django.http import HttpRequest
from rest_framework.test import APITestCase


class BaseTestCase(APITestCase):
    """
    Class that help login client
    """
    def login(self, user):
        """
        User login.
        :param user: User object
        """
        password = "!QAZxsw2"
        user.set_password(password)
        user.save()

        assert self.client.login(request=HttpRequest(), username=user.username, password=password)
