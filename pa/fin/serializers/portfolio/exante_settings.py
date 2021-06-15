from rest_framework import serializers

from fin.models.portfolio import ExanteSettings


class ExanteSettingsSerializer(serializers.ModelSerializer):
    exante_account_id = serializers.CharField(max_length=50, label='Exante Account ID')
    iss = serializers.CharField(max_length=50, label='ISS')
    sub = serializers.CharField(max_length=50, label='SUB')

    class Meta:
        model = ExanteSettings
        fields = ('exante_account_id', 'id', 'iss', 'sub', 'portfolio')
