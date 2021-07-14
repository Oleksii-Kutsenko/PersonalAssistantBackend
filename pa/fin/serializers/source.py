from rest_framework import serializers

from fin.models.index import Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ('id', 'name', 'url')
