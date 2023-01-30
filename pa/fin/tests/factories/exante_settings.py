"""
Exante Settings factory
"""
import factory

from fin.models.portfolio import ExanteSettings


class ExanteSettingsFactory(factory.DjangoModelFactory):
    """
    Creates ExanteSettings for tests
    """

    class Meta:
        """
        Meta
        """

        model = ExanteSettings
