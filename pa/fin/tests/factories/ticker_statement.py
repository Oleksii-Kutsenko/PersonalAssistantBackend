"""
TickerStatement Factory
"""
import factory

from fin.models.ticker import TickerStatement


class TickerStatementFactory(factory.DjangoModelFactory):
    """
    Creates TickerStatement object
    """

    class Meta:
        """
        Factory meta class
        """
        model = TickerStatement
