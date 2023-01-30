"""
The Index model serializer
"""

from django.db.models import DecimalField, Count, Min
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueValidator

from fin.models.index import Index, Source
from fin.models.utils import MAX_DIGITS, DECIMAL_PLACES, UpdatingStatus
from fin.serializers.utils import PrimaryKeyRelatedField


class BaseIndexSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    tickers_last_updated = SerializerMethodField(read_only=True)

    def get_name(self, obj):
        """
        Get the human-readable name of the index
        """
        return obj.source.name

    def get_tickers_last_updated(self, obj):
        """
        Returns portfolio tickers last updated time
        """
        return obj.tickers.aggregate(Min("updated")).get("updated__min")

    class Meta:
        model = Index
        fields = ("id", "source", "name", "status", "tickers_last_updated", "updated")
        read_only_fields = ("id", "name", "status", "updated")


# pylint: disable=no-self-use
class IndexSerializer(BaseIndexSerializer):
    """
    Serialization class for the relation between indexes and tickers
    """

    source = PrimaryKeyRelatedField(
        queryset=Source.objects.all(),
        validators=[UniqueValidator(Index.objects.all())],
        view_name="sources-list",
    )
    status = SerializerMethodField(read_only=True)

    def get_status(self, obj):
        """
        Returns Updating Status
        """
        return UpdatingStatus(obj.status).label

    class Meta:
        """
        Serializer meta class
        """

        model = BaseIndexSerializer.Meta.model
        fields = BaseIndexSerializer.Meta.fields
        read_only_fields = BaseIndexSerializer.Meta.read_only_fields


class DetailIndexSerializer(BaseIndexSerializer):
    """
    Serializer that includes industries/sectors breakdown
    """

    industries_breakdown = SerializerMethodField(read_only=True)
    sectors_breakdown = SerializerMethodField(read_only=True)

    def get_industries_breakdown(self, obj):
        """
        Returns list of industries and their percentage in the portfolio
        """
        decimal_field = DecimalField(
            max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES
        )

        count = float(obj.tickers.count())
        query = obj.tickers.values("industry").annotate(
            percentage=Cast(Count("industry") / count * float(100), decimal_field)
        )
        return query

    def get_sectors_breakdown(self, obj):
        """
        Returns list of sectors and their percentage in the portfolio
        """
        decimal_field = DecimalField(
            max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES
        )

        count = float(obj.tickers.count())
        query = obj.tickers.values("sector").annotate(
            percentage=Cast(Count("sector") / count * float(100), decimal_field)
        )
        return query

    class Meta:
        """
        Meta
        """

        model = BaseIndexSerializer.Meta.model
        fields = BaseIndexSerializer.Meta.fields + (
            "industries_breakdown",
            "sectors_breakdown",
        )
        read_only_fields = BaseIndexSerializer.Meta.read_only_fields
