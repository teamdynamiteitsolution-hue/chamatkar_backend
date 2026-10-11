from django.contrib import admin
from .models import Product, Coupon, Review

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'regularPrice', 'stock', 'rating')
    search_fields = ('name', 'nameBn', 'sku', 'category')
    list_filter = ('category', 'isHotDeal')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discountType', 'value', 'minSpend', 'isActive')
    list_filter = ('isActive', 'discountType')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'rating', 'location', 'is_verified_purchase', 'is_approved', 'source', 'created_at')
    list_filter = ('is_approved', 'rating', 'source')
    search_fields = ('customer_name', 'comment', 'location', 'order_id')

