"""
Serializers
"""
from rest_framework import serializers

from fin.models.models import Goal


class GoalSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialization class for the Goal model
    """
    id = serializers.IntegerField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['current_money_amount'] = \
            'Target money amount must be greater or equals to the current money amount'

    def validate(self, attrs):
        data = super().validate(attrs)

        if data['current_money_amount'] > data['target_money_amount']:
            raise serializers.ValidationError(
                {'current_money_amount': self.error_messages['current_money_amount']}
            )

        return data

    class Meta:
        """
        Serializer meta class
        """
        model = Goal
        fields = '__all__'
