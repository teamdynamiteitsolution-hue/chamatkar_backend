from rest_framework import serializers
from .models import AuditLog, MarketingEvent, NotificationLog, MarketingConfig, ShopSetting, StaffMember

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'timestamp', 'actor', 'role', 'action', 'targetType', 'targetId', 'details', 'ipAddress']

class MarketingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingEvent
        fields = ['id', 'eventId', 'eventName', 'timestamp', 'browserReported', 'serverCapiReported', 'source', 'campaign', 'value', 'orderId', 'productName', 'productId', 'dedupMatched']

class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ['id', 'orderId', 'channel', 'recipient', 'templateName', 'messageText', 'status', 'timestamp', 'provider']

class MarketingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingConfig
        fields = [
            'id', 'pixelId', 'capiToken', 'ga4Id', 'testEventCode', 'adAccountId',
            'targetScope', 'targetProductId', 'targetLandingSlug',
            'isActive', 'updated_at'
        ]

class ShopSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSetting
        fields = [
            'id', 'shopName', 'shopTagline', 'hotline', 'whatsappNumber',
            'supportEmail', 'address', 'logoUrl', 'faviconUrl',
            'whatsappProvider', 'whatsappToken', 'whatsappPhoneNumberId',
            'whatsappInstanceId', 'adminAlertPhone', 'whatsappEnabled',
            'emailHost', 'emailPort', 'emailUseTls', 'emailUseSsl',
            'emailHostUser', 'emailHostPassword', 'defaultFromEmail', 'emailEnabled',
            'shopLanguageMode', 'defaultLanguage',
            'updated_at'
        ]

class StaffMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMember
        fields = [
            'id', 'name', 'username', 'phone', 'email', 'role',
            'status', 'notes', 'created_at', 'updated_at'
        ]


