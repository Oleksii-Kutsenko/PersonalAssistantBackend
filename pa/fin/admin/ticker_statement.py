"""
Admin stuff for Ticker Statement
"""
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from fin.models.ticker import TickerStatement


class TickerStatementAdmin(ModelAdmin):
    """
    Adds ticker statement model to the admin panel
    """


admin.site.register(TickerStatement, TickerStatementAdmin)
