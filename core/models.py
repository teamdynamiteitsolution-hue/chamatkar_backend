import uuid
from django.db import models
from django.utils import timezone

class AuditLog(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('OPERATIONS', 'Operations'),
        ('MARKETING', 'Marketing'),
        ('SYSTEM', 'System'),
    ]
    TARGET_TYPE_CHOICES = [
        ('ORDER', 'Order'),
        ('PRODUCT', 'Product'),
        ('COURIER', 'Courier'),
        ('PAYMENT', 'Payment'),
        ('SETTINGS', 'Settings'),
    ]

    id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.CharField(max_length=50)
    actor = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='SYSTEM')
    action = models.CharField(max_length=100)
    targetType = models.CharField(max_length=50, choices=TARGET_TYPE_CHOICES)
    targetId = models.CharField(max_length=100)
    details = models.TextField()
    ipAddress = models.CharField(max_length=50, default='127.0.0.1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def log(cls, actor='SYSTEM', role='SYSTEM', action='UNKNOWN', target_type='SYSTEM', target_id='', details='', ip_address='127.0.0.1'):
        now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        log_id = f"aud-{int(timezone.now().timestamp() * 1000)}-{uuid.uuid4().hex[:4]}"
        return cls.objects.create(
            id=log_id,
            timestamp=now_str,
            actor=actor,
            role=role,
            action=action,
            targetType=target_type,
            targetId=target_id,
            details=details,
            ipAddress=ip_address
        )


class MarketingEvent(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    eventId = models.CharField(max_length=100, blank=True, null=True)
    eventName = models.CharField(max_length=100)
    timestamp = models.CharField(max_length=50)
    browserReported = models.BooleanField(default=False)
    serverCapiReported = models.BooleanField(default=True)
    source = models.CharField(max_length=100, default='direct')
    campaign = models.CharField(max_length=100, blank=True, null=True)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    orderId = models.CharField(max_length=100, blank=True, null=True)
    productName = models.CharField(max_length=255, blank=True, null=True)
    productId = models.CharField(max_length=100, blank=True, null=True)
    dedupMatched = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class NotificationLog(models.Model):
    CHANNEL_CHOICES = [
        ('SMS', 'SMS'),
        ('WHATSAPP', 'WhatsApp'),
        ('EMAIL', 'Email'),
    ]
    STATUS_CHOICES = [
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]

    id = models.CharField(max_length=64, primary_key=True)
    orderId = models.CharField(max_length=100)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=100)
    templateName = models.CharField(max_length=100)
    messageText = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SENT')
    timestamp = models.CharField(max_length=50)
    provider = models.CharField(max_length=100, default='Greenweb_SMS')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MarketingConfig(models.Model):
    SCOPE_CHOICES = [
        ('GLOBAL', 'Global (Entire Store)'),
        ('PRODUCT', 'Specific Product'),
        ('LANDING', 'Specific Landing Page'),
    ]

    id = models.CharField(max_length=64, primary_key=True, default='default_config')
    pixelId = models.CharField(max_length=100, blank=True, default='')
    capiToken = models.TextField(blank=True, default='')
    ga4Id = models.CharField(max_length=100, blank=True, default='')
    testEventCode = models.CharField(max_length=100, blank=True, default='')
    adAccountId = models.CharField(max_length=100, blank=True, default='')
    targetScope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='GLOBAL')
    targetProductId = models.CharField(max_length=100, blank=True, default='')
    targetLandingSlug = models.CharField(max_length=100, blank=True, default='')
    isActive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"MarketingConfig({self.targetScope}) - Pixel: {self.pixelId}"


class ShopSetting(models.Model):
    WHATSAPP_CHOICES = [
        ('META_CLOUD', 'Meta WhatsApp Cloud API'),
        ('ULTRAMSG', 'UltraMsg WhatsApp API'),
    ]

    id = models.CharField(max_length=64, primary_key=True, default='default_shop_setting')
    shopName = models.CharField(max_length=200, default='Chamatkar BD')
    shopTagline = models.TextField(blank=True, default='বাংলাদেশের ১ নম্বর ট্রাস্টেড প্রিমিয়াম গ্যাজেট ও লাইফস্টাইল শপ')
    hotline = models.CharField(max_length=50, default='09612345678')
    whatsappNumber = models.CharField(max_length=50, default='01712849201')
    supportEmail = models.CharField(max_length=150, default='support@chamatkar.com')
    address = models.TextField(blank=True, default='Chamatkar Head Office, Dhanmondi 27, Dhaka, Bangladesh')
    logoUrl = models.TextField(blank=True, default='')
    faviconUrl = models.TextField(blank=True, default='')
    headerLogoUrl = models.TextField(blank=True, default='')
    footerLogoUrl = models.TextField(blank=True, default='')
    extraConfig = models.JSONField(default=dict, blank=True)

    # WhatsApp Gateway Configuration
    whatsappProvider = models.CharField(max_length=30, choices=WHATSAPP_CHOICES, default='META_CLOUD')
    whatsappToken = models.TextField(blank=True, default='')
    whatsappPhoneNumberId = models.CharField(max_length=100, blank=True, default='')
    whatsappInstanceId = models.CharField(max_length=100, blank=True, default='')
    adminAlertPhone = models.CharField(max_length=50, blank=True, default='')
    whatsappEnabled = models.BooleanField(default=True)

    # SMTP Email Gateway Configuration
    emailHost = models.CharField(max_length=150, default='smtp.gmail.com', blank=True)
    emailPort = models.IntegerField(default=587)
    emailUseTls = models.BooleanField(default=True)
    emailUseSsl = models.BooleanField(default=False)
    emailHostUser = models.CharField(max_length=150, blank=True, default='')
    emailHostPassword = models.CharField(max_length=255, blank=True, default='')
    defaultFromEmail = models.CharField(max_length=200, blank=True, default='Chamatkar BD <orders@chamatkar.com>')
    emailEnabled = models.BooleanField(default=True)
    # Shop Language & Translation Configuration
    LANGUAGE_MODE_CHOICES = [
        ('both', 'উভয় ভাষা (Both / Multi-Language)'),
        ('bn', 'শুধুমাত্র বাংলা (Bengali Only)'),
        ('en', 'Only English (English Only)'),
    ]
    shopLanguageMode = models.CharField(max_length=10, choices=LANGUAGE_MODE_CHOICES, default='both')
    defaultLanguage = models.CharField(max_length=5, default='bn', choices=[('bn', 'বাংলা'), ('en', 'English')])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"ShopSetting: {self.shopName}"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            id='default_shop_setting',
            defaults={
                'shopName': 'Chamatkar BD',
                'shopTagline': 'বাংলাদেশের ১ নম্বর ট্রাস্টেড প্রিমিয়াম গ্যাজেট ও লাইফস্টাইল শপ',
                'hotline': '09612345678',
                'whatsappNumber': '01712849201',
                'supportEmail': 'support@chamatkar.com',
                'address': 'Chamatkar Head Office, Dhanmondi 27, Dhaka, Bangladesh',
                'whatsappProvider': 'META_CLOUD',
                'whatsappEnabled': True
            }
        )
        return obj


class StaffMember(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Super Admin'),
        ('MANAGER', 'Operations Manager'),
        ('DISPATCHER', 'Logistics Dispatcher'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
    ]

    id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    username = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.CharField(max_length=150, blank=True, default='')
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MANAGER')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} (@{self.username}) - {self.role}"

    @classmethod
    def seed_defaults_if_empty(cls):
        if cls.objects.count() == 0:
            cls.objects.create(
                id='staff-admin-root',
                name='সুপার অ্যাডমিন (Owner)',
                username='admin',
                phone='01712849201',
                email='admin@chamatkar.com',
                password='admin1234',
                role='ADMIN',
                status='ACTIVE',
                notes='Primary store owner with full unrestricted authority'
            )
            cls.objects.create(
                id='staff-manager-demo',
                name='অপারেশনস ম্যানেজার (Operations)',
                username='manager',
                phone='01812345678',
                email='manager@chamatkar.com',
                password='manager1234',
                role='MANAGER',
                status='ACTIVE',
                notes='Manages daily operations, stock, orders, and customer queries'
            )
            cls.objects.create(
                id='staff-dispatcher-demo',
                name='ডেলিভারি ডিসপ্যাচার (Logistics)',
                username='dispatcher',
                phone='01912345678',
                email='dispatcher@chamatkar.com',
                password='dispatcher1234',
                role='DISPATCHER',
                status='ACTIVE',
                notes='Fulfills orders, prints packing slips, and hands over to Steadfast/Pathao/RedX'
            )

