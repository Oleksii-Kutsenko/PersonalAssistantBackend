"""
Serializers
"""
from rest_framework import serializers

from fin.models.models import Account, Goal


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Account model
    """
    id = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta"""
        model = Account
        fields = '__all__'


class GoalSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Goal model
    """
    id = serializers.IntegerField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(GoalSerializer, self).__init__(*args, **kwargs)
        self.error_messages['current_money_amount'] = \
            'Target money amount must be greater or equals to the current money amount'

    def validate(self, attrs):
        data = super().validate(attrs)

        if data['current_money_amount'] > data['target_money_amount']:
            raise serializers.ValidationError({'current_money_amount': self.error_messages['current_money_amount']})

        return data

    class Meta:
        model = Goal
        fields = '__all__'
