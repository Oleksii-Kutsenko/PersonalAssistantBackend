"""
Users app models
"""
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user for PA project
    """
