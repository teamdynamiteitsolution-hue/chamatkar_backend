from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health_check, name='health_check'),
    path('audit-logs', views.audit_logs_list, name='audit_logs'),
    path('marketing/config', views.marketing_config_view, name='marketing_config'),
    path('marketing/capi/event', views.marketing_capi_event_view, name='marketing_capi_event'),
    path('marketing/events', views.marketing_events_view, name='marketing_events'),
    path('marketing/sync-meta-ads', views.sync_meta_ads_view, name='sync_meta_ads'),
    path('marketing/facebook-catalog.xml', views.facebook_catalog_feed_view, name='facebook_catalog_feed'),
    path('notifications', views.notifications_list, name='notifications'),
    path('settings/shop', views.shop_settings_view, name='shop_settings'),
    path('settings/shop/', views.shop_settings_view, name='shop_settings_slash'),
    path('settings/whatsapp/test', views.test_whatsapp_view, name='test_whatsapp'),
    path('settings/whatsapp/test/', views.test_whatsapp_view, name='test_whatsapp_slash'),
    path('settings/email/test', views.test_email_view, name='test_email'),
    path('settings/email/test/', views.test_email_view, name='test_email_slash'),
    path('staff', views.staff_list_or_create, name='staff_list_or_create'),
    path('staff/', views.staff_list_or_create, name='staff_list_or_create_slash'),
    path('staff/<str:staff_id>', views.staff_detail_update_delete, name='staff_detail_update_delete'),
    path('staff/<str:staff_id>/', views.staff_detail_update_delete, name='staff_detail_update_delete_slash'),
    path('staff-auth/login', views.staff_login_view, name='staff_login'),
    path('staff-auth/login/', views.staff_login_view, name='staff_login_slash'),
]


