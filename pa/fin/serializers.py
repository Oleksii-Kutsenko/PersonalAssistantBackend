from rest_framework import serializers

from .models import Account, Index


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Account
        fields = '__all__'


class IndexSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Index
        fields = '__all__'
