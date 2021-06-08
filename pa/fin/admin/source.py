"""
Admin stuff for Source model
"""
from django.contrib import admin

from fin.models.index import Source
from fin.models.index.source import ISharesSourceParams


class SourceAdmin(admin.ModelAdmin):
    """
    Adds Source model to the admin panel
    """


admin.site.register(Source, SourceAdmin)


class ISharesSourceParamsAdmin(admin.ModelAdmin):
    """
    Adds ISharesSourceParams model to the admin panel
    """


admin.site.register(ISharesSourceParams, ISharesSourceParamsAdmin)
