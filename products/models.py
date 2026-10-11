# pyrefly: ignore [missing-import]
from django.db import models

class Product(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    nameBn = models.CharField(max_length=255, default='', blank=True)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=100)
    price = models.IntegerField(default=0)
    regularPrice = models.IntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True)
    stock = models.IntegerField(default=20)
    isOutOfStock = models.BooleanField(default=False)
    images = models.JSONField(default=list)
    shortDescription = models.TextField(blank=True, default='')
    shortDescriptionBn = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    descriptionBn = models.TextField(blank=True, default='')
    features = models.JSONField(default=list)
    featuresBn = models.JSONField(default=list, blank=True)
    featureDetails = models.JSONField(default=list, blank=True)
    video360 = models.TextField(blank=True, default='')
    variants = models.JSONField(default=list, blank=True)
    productType = models.CharField(max_length=50, default='standard', blank=True)
    rating = models.FloatField(default=4.8)
    reviewsCount = models.IntegerField(default=1)
    isHotDeal = models.BooleanField(default=False)
    badge = models.CharField(max_length=50, blank=True, default='')
    warranty = models.CharField(max_length=100, blank=True, default='')
    deliveryDays = models.CharField(max_length=100, default='2-3 Days')
    sortOrder = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sortOrder', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed'),
    ]

    code = models.CharField(max_length=50, primary_key=True)
    discountType = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='fixed')
    value = models.IntegerField(default=0)
    minSpend = models.IntegerField(default=0)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.discountType} - {self.value})"


class Review(models.Model):
    SOURCE_CHOICES = [
        ('ORDER_TRACKING', 'Order Tracking (Customer)'),
        ('ADMIN_MANUAL', 'Admin Manual Entry'),
        ('STOREFRONT', 'Storefront Direct'),
    ]

    id = models.CharField(max_length=64, primary_key=True)
    order_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    product_name = models.CharField(max_length=255, blank=True, default='')
    customer_name = models.CharField(max_length=128)
    customer_phone = models.CharField(max_length=32, blank=True, default='')
    location = models.CharField(max_length=128, blank=True, default='')
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default='ORDER_TRACKING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} ({self.rating}★) - {self.comment[:30]}"

