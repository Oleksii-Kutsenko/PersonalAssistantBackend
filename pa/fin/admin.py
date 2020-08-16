from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.options import TabularInline

from fin.models.portfolio import Portfolio
from fin.models.ticker import TickerStatement, Ticker


class TickerInlineAdmin(TabularInline):
    model = Portfolio.tickers.through


class PortfolioAdmin(ModelAdmin):
    fields = ('name', 'user')

    inlines = (TickerInlineAdmin,)


admin.site.register(Portfolio, PortfolioAdmin)


class CompanyInfoAdmin(admin.ModelAdmin):
    pass


admin.site.register(TickerStatement, CompanyInfoAdmin)


class TickerAdmin(admin.ModelAdmin):
    pass


admin.site.register(Ticker, TickerAdmin)
