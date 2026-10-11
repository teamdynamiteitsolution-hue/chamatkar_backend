from django.urls import path
from . import views

urlpatterns = [
    path('couriers', views.couriers_list, name='couriers_list'),
    path('couriers/assign', views.assign_courier, name='assign_courier'),
    path('couriers/<str:provider>/balance', views.courier_balance, name='courier_balance'),
    path('couriers/<str:provider>/status/<str:tracking_code>', views.courier_check_status, name='courier_check_status'),
    path('couriers/<str:pk>', views.courier_update, name='courier_update'),
    path('webhooks/couriers', views.courier_webhook, name='courier_webhook'),
    path('webhooks/couriers/<str:provider>', views.provider_webhook, name='provider_webhook'),
]
