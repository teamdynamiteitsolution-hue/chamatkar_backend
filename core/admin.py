from django.contrib import admin
from .models import AuditLog, MarketingEvent, NotificationLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'actor', 'role', 'action', 'targetType', 'targetId')
    list_filter = ('role', 'targetType', 'action')
    search_fields = ('actor', 'targetId', 'details')

@admin.register(MarketingEvent)
class MarketingEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'eventName', 'source', 'campaign', 'value', 'timestamp')
    list_filter = ('eventName', 'source')

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'orderId', 'channel', 'recipient', 'templateName', 'status', 'timestamp')
    list_filter = ('channel', 'status', 'provider')
