"""
Admin stuff for Stock Exchange model
"""
from django.contrib import admin
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from fin.models.stock_exchange import StockExchange


class StockExchangeAdmin(admin.ModelAdmin, DynamicArrayMixin):
    """
    Adds Stock Exchange model to the admin panel
    """


admin.site.register(StockExchange, StockExchangeAdmin)
