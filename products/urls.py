from django.urls import path
from . import views

urlpatterns = [
    path('products/bulk-stock', views.bulk_update_stock, name='bulk_update_stock'),
    path('products/reorder', views.reorder_products, name='reorder_products'),
    path('products', views.products_list_create, name='products_list_create'),
    path('products/<str:pk>', views.product_detail_update, name='product_detail_update'),
    path('upload/image', views.upload_image_view, name='upload_image'),
    path('coupons', views.coupons_list_or_create, name='coupons_list_or_create'),
    path('coupons/', views.coupons_list_or_create, name='coupons_list_or_create_slash'),
    path('coupons/<str:code>', views.coupon_detail_update_delete, name='coupon_detail_update_delete'),
    path('coupons/<str:code>/', views.coupon_detail_update_delete, name='coupon_detail_update_delete_slash'),
    path('reviews', views.reviews_list_create, name='reviews_list_create'),
    path('reviews/<str:pk>', views.review_detail_update_delete, name='review_detail_update_delete'),
]
