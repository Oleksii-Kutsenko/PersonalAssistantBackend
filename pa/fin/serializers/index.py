"""
The Index model serializer
"""
from rest_framework import serializers

from fin.models.index import Index


# pylint: disable=no-self-use
class IndexSerializer(serializers.ModelSerializer):
    """
    Serialization class for the relation between indexes and tickers
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        """
        Get the human-readable name of the index
        """
        return dict(Index.Source.choices)[obj.data_source_url]

    class Meta:
        """
        Serializer meta class
        """
        model = Index
        fields = ('id', 'data_source_url', 'name', 'tickers')
