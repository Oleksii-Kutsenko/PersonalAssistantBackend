from rest_framework import serializers

from .models import Account, Record


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
