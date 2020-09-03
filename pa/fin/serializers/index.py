"""
The Index model serializer
"""

from django.db.models import DecimalField, Count
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from fin.models.index import Index
from fin.models.index.parsers import Source
from fin.models.utils import MAX_DIGITS, DECIMAL_PLACES


# pylint: disable=no-self-use
class IndexSerializer(serializers.ModelSerializer):
    """
    Serialization class for the relation between indexes and tickers
    """
    id = serializers.IntegerField(read_only=True)
    industries_breakdown = SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField()
    sectors_breakdown = SerializerMethodField(read_only=True)

    def get_industries_breakdown(self, obj):
        """
        Returns list of industries and their percentage in the portfolio
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)

        count = float(obj.tickers.count())
        query = obj.tickers.values('industry') \
            .annotate(percentage=Cast(Count('industry') / count * float(100), decimal_field))
        return query

    def get_name(self, obj):
        """
        Get the human-readable name of the index
        """
        return dict(Source.choices)[obj.data_source_url]

    def get_sectors_breakdown(self, obj):
        """
        Returns list of sectors and their percentage in the portfolio
        """
        decimal_field = DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)

        count = float(obj.tickers.count())
        query = obj.tickers.values('sector') \
            .annotate(percentage=Cast(Count('sector') / count * float(100), decimal_field))
        return query

    class Meta:
        """
        Serializer meta class
        """
        model = Index

        fields = ('id', 'data_source_url', 'industries_breakdown', 'name', 'sectors_breakdown')
