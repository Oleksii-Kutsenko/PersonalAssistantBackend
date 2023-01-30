"""
The source model related serializers
"""
from rest_framework import serializers

from fin.models.index import Source


# pylint: disable=missing-class-docstring
class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ("id", "name", "url")
