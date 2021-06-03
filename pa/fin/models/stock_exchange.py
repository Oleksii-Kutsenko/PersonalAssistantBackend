from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField


class StockExchange(models.Model):
    name = models.CharField(max_length=100, unique=True)
    aliases = ArrayField(models.CharField(max_length=50))

    def __str__(self):
        return self.name

    @classmethod
    def get_stock_exchanges_mapper(cls):
        stock_exchanges_mapper = dict()
        for se in cls.objects.all():
            for alias in se.aliases:
                stock_exchanges_mapper[alias] = se.id
        return stock_exchanges_mapper
