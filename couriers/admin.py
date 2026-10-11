from django.contrib import admin
from .models import CourierConfig

@admin.register(CourierConfig)
class CourierConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'isActive', 'insideDhakaRate', 'outsideDhakaRate', 'codFeePercent', 'lastSyncTime')
    list_filter = ('isActive',)
