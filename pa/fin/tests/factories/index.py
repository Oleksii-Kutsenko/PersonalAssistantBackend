"""
Index Factory
"""
import factory
from factory.fuzzy import FuzzyChoice

from fin.models.index import Index, Source


class IndexFactory(factory.DjangoModelFactory):
    """
    Creates Index object
    """

    class Meta:
        """
        Factory meta class
        """

        model = Index

    source = FuzzyChoice(choices=Source.objects.filter(updatable=True).all())
