"""
User Factory
"""
import factory

from users.models import User


class UserFactory(factory.DjangoModelFactory):
    """
    Creates Account objects
    """

    class Meta:
        """
        Meta
        """

        model = User

    username = factory.Faker("pystr", max_chars=150)
