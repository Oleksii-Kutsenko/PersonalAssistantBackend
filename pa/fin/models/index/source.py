"""
Data Source and related models
"""
from django.db import models
from django.utils.functional import cached_property

from fin.models.index.parsers import AmplifyParser, InvescoCSVParser, ISharesParser


class ISharesSourceParams(models.Model):
    """
    The model that represents extra params for parsing the IShares ETFs
    """
    data_type = models.CharField(max_length=20)
    file_name = models.CharField(max_length=20)
    file_type = models.CharField(max_length=20)
    source = models.OneToOneField('Source', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.source)


class Source(models.Model):
    """
    The models that represents data source
    """
    parsers_mapper = {
        'AmplifyParser': AmplifyParser,
        'InvescoCSVParser': InvescoCSVParser,
        'ISharesParser': ISharesParser
    }

    parser_name = models.CharField(choices=[(k, k) for k in parsers_mapper.keys()], max_length=50)
    name = models.CharField(max_length=100)
    updatable = models.BooleanField(default=True)
    url = models.URLField()

    def __init__(self, *args, **kwargs):
        self._parser = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    @cached_property
    def parser(self):
        """
        Creates the parser instance and caches it
        """
        if self._parser is None:
            self._parser = self.parsers_mapper[self.parser_name](self)
        return self._parser
