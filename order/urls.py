from django.urls import path
from . import views

urlpatterns = [
    path('checkout', views.checkout_view, name='checkout'),
    path('orders', views.orders_list, name='orders_list'),
    path('orders/<str:pk>', views.order_detail, name='order_detail'),
    path('orders/<str:pk>/status', views.update_order_status, name='update_order_status'),
    path('tracking/lookup', views.tracking_lookup, name='tracking_lookup'),
]
