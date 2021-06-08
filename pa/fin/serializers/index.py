"""
The Index model serializer
"""

from django.db.models import DecimalField, Count, Min
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from fin.models.index import Index
from fin.models.utils import MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus


# pylint: disable=no-self-use
class IndexSerializer(serializers.ModelSerializer):
    """
    Serialization class for the relation between indexes and tickers
    """
    name = serializers.SerializerMethodField()
    status = SerializerMethodField(read_only=True)
    tickers_last_updated = SerializerMethodField(read_only=True)

    def get_name(self, obj):
        """
        Get the human-readable name of the index
        """
        return obj.source.name

    def get_status(self, obj):
        """
        Returns Updating Status
        """
        return UpdatingStatus(obj.status).label

    def get_tickers_last_updated(self, obj):
        """
        Returns portfolio tickers last updated time
        """
        return obj.tickers.aggregate(Min('updated')).get('updated__min')

    class Meta:
        """
        Serializer meta class
        """
        model = Index
        fields = ('id', 'source', 'name', 'status', 'tickers_last_updated', 'updated')
        read_only_fields = ('id', 'name', 'status', 'updated')


class DetailIndexSerializer(IndexSerializer):
    """
    Serializer that includes industries/sectors breakdown
    """
    industries_breakdown = SerializerMethodField(read_only=True)
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
        Meta
        """

        model = IndexSerializer.Meta.model
        fields = IndexSerializer.Meta.fields + ('industries_breakdown', 'sectors_breakdown')
