from rest_framework import serializers
from .models import PaymentTransaction, PaymentGatewayConfig, PaymentMethodSetting

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'order_id',
            'tran_id',
            'val_id',
            'amount',
            'currency',
            'payment_method',
            'status',
            'card_type',
            'card_issuer',
            'bank_tran_id',
            'customer_name',
            'customer_phone',
            'session_key',
            'gateway_url',
            'error_reason',
            'created_at',
            'updated_at',
        ]


class PaymentGatewayConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGatewayConfig
        fields = [
            'gateway_id',
            'name',
            'store_id',
            'store_password',
            'is_sandbox',
            'is_active',
            'fee_percent',
            'updated_at',
        ]


class PaymentMethodSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethodSetting
        fields = [
            'id',
            'method_id',
            'name',
            'is_active',
            'account_type',
            'number',
            'counter',
            'instructions',
            'display_order',
            'updated_at',
        ]
