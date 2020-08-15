from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.options import TabularInline

from fin.models.portfolio import Portfolio


class TickerInlineAdmin(TabularInline):
    model = Portfolio.tickers.through


class PortfolioAdmin(ModelAdmin):
    fields = ('name', 'user')

    inlines = (TickerInlineAdmin,)


admin.site.register(Portfolio, PortfolioAdmin)
