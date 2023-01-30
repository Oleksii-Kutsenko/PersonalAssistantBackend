"""
Admin stuff for Ticker model
"""
from django.contrib import admin

from fin.models.ticker import Ticker


class TickerAdmin(admin.ModelAdmin):
    """
    Adds Ticker model to the admin panel
    """

    search_fields = ("symbol",)


admin.site.register(Ticker, TickerAdmin)
