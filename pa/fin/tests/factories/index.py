"""
Index Factory
"""
import factory
from factory.fuzzy import FuzzyChoice

from fin.models.index import Index


class IndexFactory(factory.DjangoModelFactory):
    """
    Creates Index object
    """

    class Meta:
        """
        Factory meta class
        """
        model = Index

    data_source_url = FuzzyChoice(choices=[index for index, parser in Index.url_parsers.items()
                                           if parser.updatable])
