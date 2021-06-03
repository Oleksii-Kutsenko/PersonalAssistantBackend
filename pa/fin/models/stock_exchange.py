"""
Stock exchange and related models
"""
from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField


class StockExchange(models.Model):
    """
    Model represents stock exchange
    """
    name = models.CharField(max_length=100, unique=True)
    aliases = ArrayField(models.CharField(max_length=50))

    def __str__(self):
        return f'{self.name}'

    @classmethod
    def get_stock_exchanges_mapper(cls):
        """
        Returns dict with stock exchange aliases as keys, and entity ids as values
        """
        stock_exchanges_mapper = dict()
        for stock_exchange in cls.objects.all():
            for alias in stock_exchange.aliases:
                stock_exchanges_mapper[alias] = stock_exchange.id
        return stock_exchanges_mapper
