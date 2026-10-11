from rest_framework import serializers
from .models import CourierConfig

class CourierConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierConfig
        fields = [
            'id', 'name', 'logo', 'isActive', 'apiKey', 'secret',
            'coverage', 'codFeePercent', 'insideDhakaRate', 'outsideDhakaRate',
            'lastSyncTime', 'pendingCodAmount', 'settledCodAmount'
        ]
