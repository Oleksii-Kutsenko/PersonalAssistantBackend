"""
Admin stuff for Stock Exchange model
"""
from django.contrib import admin

from fin.models.stock_exchange import StockExchange


class StockExchangeAdmin(admin.ModelAdmin):
    """
    Adds Stock Exchange model to the admin panel
    """
    list_display = ('name', 'available',)
    list_filter = ('available',)


admin.site.register(StockExchange, StockExchangeAdmin)
