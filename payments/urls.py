from django.urls import path
from .views import (
    initiate_payment_view,
    sslcommerz_success_listener,
    sslcommerz_fail_listener,
    sslcommerz_cancel_listener,
    sslcommerz_ipn_listener,
    sandbox_simulator_view,
    payment_transactions_list,
    payment_config_view,
    payment_verify_view,
    payment_methods_view,
)

urlpatterns = [
    # Payment Methods & Channels Configuration
    path('payments/methods', payment_methods_view, name='payment_methods'),
    path('payments/methods/', payment_methods_view, name='payment_methods_slash'),

    # SSLCommerz Payment Session Initiate
    path('payments/initiate', initiate_payment_view, name='payment_initiate'),
    path('payments/initiate/', initiate_payment_view, name='payment_initiate_slash'),

    # SSLCommerz Callbacks
    path('payments/sslcommerz/success', sslcommerz_success_listener, name='sslcommerz_success'),
    path('payments/sslcommerz/success/', sslcommerz_success_listener, name='sslcommerz_success_slash'),
    path('payments/sslcommerz/fail', sslcommerz_fail_listener, name='sslcommerz_fail'),
    path('payments/sslcommerz/fail/', sslcommerz_fail_listener, name='sslcommerz_fail_slash'),
    path('payments/sslcommerz/cancel', sslcommerz_cancel_listener, name='sslcommerz_cancel'),
    path('payments/sslcommerz/cancel/', sslcommerz_cancel_listener, name='sslcommerz_cancel_slash'),
    path('payments/sslcommerz/ipn', sslcommerz_ipn_listener, name='sslcommerz_ipn'),
    path('payments/sslcommerz/ipn/', sslcommerz_ipn_listener, name='sslcommerz_ipn_slash'),

    # Built-in Interactive SSLCommerz Sandbox Simulator
    path('payments/sslcommerz/sandbox-simulator', sandbox_simulator_view, name='sslcommerz_simulator'),
    path('payments/sslcommerz/sandbox-simulator/', sandbox_simulator_view, name='sslcommerz_simulator_slash'),

    # Admin Transactions, Config, and Verification APIs
    path('payments/transactions', payment_transactions_list, name='payment_transactions'),
    path('payments/transactions/', payment_transactions_list, name='payment_transactions_slash'),
    path('payments/config', payment_config_view, name='payment_config'),
    path('payments/config/', payment_config_view, name='payment_config_slash'),
    path('payments/verify', payment_verify_view, name='payment_verify'),
    path('payments/verify/', payment_verify_view, name='payment_verify_slash'),
]
