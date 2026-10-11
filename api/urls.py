from django.urls import path, include
from .views import api_status, trigger_migration

urlpatterns = [
    path('', api_status, name='api_status'),
    path('system/migrate', trigger_migration, name='trigger_migration'),
    path('', include('core.urls')),
    path('', include('products.urls')),
    path('', include('order.urls')),
    path('', include('couriers.urls')),
    path('', include('ai_assistant.urls')),
    path('', include('users.urls')),
    path('', include('payments.urls')),
    path('', include('translator.urls')),
]
