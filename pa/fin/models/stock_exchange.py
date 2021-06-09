"""
Stock exchange and related models
"""
from django.db import models


class StockExchange(models.Model):
    """
    Model represents stock exchange
    """
    available = models.BooleanField(default=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{self.name}'


class StockExchangeAlias(models.Model):
    """
    Model represents stock exchanges aliases
    """
    alias = models.CharField(max_length=50)
    stock_exchange = models.ForeignKey('StockExchange', on_delete=models.CASCADE)
