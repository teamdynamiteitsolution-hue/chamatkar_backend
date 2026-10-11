from django.db import models

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('VALIDATED', 'Validated / Successful'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    order_id = models.CharField(max_length=64, db_index=True)
    tran_id = models.CharField(max_length=128, unique=True, db_index=True)
    val_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    payment_method = models.CharField(max_length=32, default='SSLCOMMERZ')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    card_type = models.CharField(max_length=64, blank=True, null=True)
    card_issuer = models.CharField(max_length=128, blank=True, null=True)
    bank_tran_id = models.CharField(max_length=128, blank=True, null=True)
    customer_name = models.CharField(max_length=128, blank=True, null=True)
    customer_phone = models.CharField(max_length=32, blank=True, null=True)
    session_key = models.CharField(max_length=256, blank=True, null=True)
    gateway_url = models.TextField(blank=True, null=True)
    error_reason = models.TextField(blank=True, null=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tran_id} ({self.order_id}) - ৳{self.amount} [{self.status}]"


class PaymentGatewayConfig(models.Model):
    gateway_id = models.CharField(max_length=32, unique=True, default='sslcommerz')
    name = models.CharField(max_length=64, default='SSLCOMMERZ Multi-Card Gateway')
    store_id = models.CharField(max_length=128, default='testbox')
    store_password = models.CharField(max_length=128, default='qwerty')
    is_sandbox = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    fee_percent = models.DecimalField(max_digits=4, decimal_places=2, default=2.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({'Sandbox' if self.is_sandbox else 'Live'})"


class PaymentMethodSetting(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('MERCHANT', 'Merchant (Payment)'),
        ('PERSONAL', 'Personal (Send Money)'),
        ('AGENT', 'Agent (Cash Out)'),
        ('GATEWAY', 'Online Gateway'),
        ('COD', 'Cash on Delivery'),
    ]

    method_id = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES, default='MERCHANT')
    number = models.CharField(max_length=32, blank=True, default='')
    counter = models.CharField(max_length=16, blank=True, default='1')
    instructions = models.TextField(blank=True, default='')
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.name} [{self.method_id}] ({'Active' if self.is_active else 'Disabled'})"
