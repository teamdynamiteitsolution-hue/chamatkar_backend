from django.db import models

class Order(models.Model):
    ORDER_STATUS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COURIER_CREATED', 'Courier Created'),
        ('PICKED_UP', 'Picked Up'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURNED', 'Returned'),
        ('DELIVERY_FAILED', 'Delivery Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_METHODS = [
        ('COD', 'Cash on Delivery'),
        ('BKASH', 'bKash'),
        ('NAGAD', 'Nagad'),
        ('ROCKET', 'Rocket'),
        ('SSLCOMMERZ', 'SSLCommerz'),
    ]

    PAYMENT_STATUS = [
        ('UNPAID', 'Unpaid'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUND_PENDING', 'Refund Pending'),
        ('REFUNDED', 'Refunded'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    trackingToken = models.CharField(max_length=100, unique=True)
    createdAt = models.CharField(max_length=50)
    
    # Store complete item snapshots and address snapshots
    items = models.JSONField(default=list)
    address = models.JSONField(default=dict)
    customerEmail = models.EmailField(max_length=254, blank=True, null=True, db_index=True)
    
    subtotal = models.IntegerField(default=0)
    deliveryFee = models.IntegerField(default=60)
    discount = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    
    paymentMethod = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='COD')
    paymentStatus = models.CharField(max_length=30, choices=PAYMENT_STATUS, default='UNPAID')
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default='PENDING')
    
    statusHistory = models.JSONField(default=list)
    courier = models.JSONField(default=dict, blank=True, null=True)
    utm = models.JSONField(default=dict, blank=True, null=True)
    
    riskScore = models.IntegerField(default=10)
    riskFactors = models.JSONField(default=list)
    internalNotes = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        customer = self.address.get('customerName', 'Customer') if isinstance(self.address, dict) else 'Customer'
        return f"{self.id} - {customer} (৳{self.total})"
