from django.contrib import admin
from .models import CustomerProfile

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'district', 'createdAt')
    search_fields = ('name', 'phone', 'email', 'district')
