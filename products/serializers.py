# pyrefly: ignore [missing-import]
from rest_framework import serializers
from .models import Product, Coupon, Review

class ProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    originalPrice = serializers.SerializerMethodField()
    tag = serializers.CharField(source='badge', required=False, allow_blank=True)
    keyFeatures = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'nameBn', 'slug', 'category', 'price', 'regularPrice',
            'originalPrice', 'sku', 'stock', 'isOutOfStock', 'image', 'images', 'shortDescription', 'shortDescriptionBn', 'description', 'descriptionBn',
            'features', 'featuresBn', 'keyFeatures', 'featureDetails', 'video360', 'variants', 'productType',
            'rating', 'reviewsCount', 'isHotDeal', 'badge', 'tag', 'warranty', 'deliveryDays', 'sortOrder'
        ]

    def get_image(self, obj):
        if obj.images and isinstance(obj.images, list) and len(obj.images) > 0:
            return obj.images[0]
        return ''

    def get_originalPrice(self, obj):
        return obj.regularPrice

    def get_keyFeatures(self, obj):
        return obj.features if isinstance(obj.features, list) else []

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discountType', 'value', 'minSpend', 'isActive']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            'id', 'order_id', 'product', 'product_name', 'customer_name',
            'customer_phone', 'location', 'rating', 'comment',
            'is_verified_purchase', 'is_approved', 'source', 'created_at', 'updated_at'
        ]

