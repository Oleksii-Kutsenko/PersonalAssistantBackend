"""
Index Factory
"""
import factory
from factory.fuzzy import FuzzyChoice

from fin.models.index import Index
from fin.models.index.parsers import Source


class IndexFactory(factory.DjangoModelFactory):
    """
    Creates Index object
    """

    class Meta:
        """
        Factory meta class
        """
        model = Index

    data_source_url = FuzzyChoice(Source)
