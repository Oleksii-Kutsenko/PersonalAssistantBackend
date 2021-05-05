"""
Admin stuff for Portfolio model
"""
from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline

from fin.models.portfolio import Portfolio


class TickerInlineAdmin(TabularInline):
    """
    Adds Portfolio Ticker M2M relation to the admin panel
    """
    model = Portfolio.tickers.through
    autocomplete_fields = ['ticker']


class PortfolioAdmin(ModelAdmin):
    """
    Adds Portfolio model to the admin panel
    """
    fields = ('name', 'user')

    inlines = (TickerInlineAdmin,)


admin.site.register(Portfolio, PortfolioAdmin)
