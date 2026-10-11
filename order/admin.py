from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'phone', 'total', 'paymentMethod', 'paymentStatus', 'status', 'createdAt')
    search_fields = ('id', 'trackingToken')
    list_filter = ('status', 'paymentMethod', 'paymentStatus')

    def customer_name(self, obj):
        if isinstance(obj.address, dict):
            return obj.address.get('customerName', '-')
        return '-'

    def phone(self, obj):
        if isinstance(obj.address, dict):
            return obj.address.get('phone', '-')
        return '-'
