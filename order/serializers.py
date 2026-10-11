from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'id', 'trackingToken', 'createdAt', 'customerEmail', 'items', 'address', 'subtotal',
            'deliveryFee', 'discount', 'total', 'paymentMethod', 'paymentStatus',
            'status', 'statusHistory', 'courier', 'utm', 'riskScore', 'riskFactors',
            'internalNotes'
        ]
