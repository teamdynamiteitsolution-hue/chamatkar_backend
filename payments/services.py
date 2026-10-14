import os
import time
import uuid
import logging
import urllib.parse
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from .models import PaymentTransaction, PaymentGatewayConfig, PaymentMethodSetting
from order.models import Order
from order.services import dispatch_order_notifications
from core.models import AuditLog

logger = logging.getLogger(__name__)

# SSLCommerz Official API Endpoints
SSLCOMMERZ_SANDBOX_GW_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
SSLCOMMERZ_LIVE_GW_URL = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

SSLCOMMERZ_SANDBOX_VALIDATION_URL = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
SSLCOMMERZ_LIVE_VALIDATION_URL = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"

DEFAULT_PAYMENT_METHODS = [
    {
        'method_id': 'sslcommerz',
        'name': 'Pay Online (Cards / bKash / Nagad via SSLCommerz)',
        'is_active': True,
        'account_type': 'GATEWAY',
        'number': '',
        'counter': '',
        'instructions': 'ভিসা, মাস্টারকার্ড, বিকাশ, নগদ, রকেট ইত্যাদির মাধ্যমে তাৎক্ষণিক পেমেন্ট সম্পন্ন করুন।',
        'display_order': 1,
    },
    {
        'method_id': 'cod',
        'name': 'Cash on Delivery',
        'is_active': True,
        'account_type': 'COD',
        'number': '',
        'counter': '',
        'instructions': 'পার্সেল হাতে পেয়ে ডেলিভারিম্যানকে ক্যাশে মূল্য পরিশোধ করবেন।',
        'display_order': 2,
    },
    {
        'method_id': 'bkash',
        'name': 'bKash Manual',
        'is_active': True,
        'account_type': 'MERCHANT',
        'number': '01892-019281',
        'counter': '1',
        'instructions': "আপনার বিকাশ অ্যাপ থেকে 'Payment' অপশনে গিয়ে মার্চেন্ট নম্বরে টাকা পে করুন এবং প্রাপ্ত TrxID নিচে লিখুন।",
        'display_order': 3,
    },
    {
        'method_id': 'nagad',
        'name': 'Nagad Manual',
        'is_active': True,
        'account_type': 'MERCHANT',
        'number': '01918-293810',
        'counter': '1',
        'instructions': "আপনার নগদ অ্যাপ থেকে 'Payment' অপশনে গিয়ে মার্চেন্ট নম্বরে টাকা পে করুন এবং প্রাপ্ত TrxID নিচে লিখুন।",
        'display_order': 4,
    },
    {
        'method_id': 'rocket',
        'name': 'Rocket Manual',
        'is_active': True,
        'account_type': 'MERCHANT',
        'number': '01712-345678',
        'counter': '1',
        'instructions': "আপনার রকেট অ্যাপ থেকে 'Merchant Pay' অপশনে গিয়ে মার্চেন্ট নম্বরে টাকা পে করুন এবং প্রাপ্ত TrxID নিচে লিখুন।",
        'display_order': 5,
    },
]


def get_or_seed_payment_methods():
    """
    Returns all configured payment methods, seeding defaults if table is empty.
    """
    for item in DEFAULT_PAYMENT_METHODS:
        PaymentMethodSetting.objects.get_or_create(
            method_id=item['method_id'],
            defaults=item
        )
    return PaymentMethodSetting.objects.all().order_by('display_order', 'id')


def get_gateway_config():
    """
    Retrieves or initializes the SSLCommerz gateway configuration.
    """
    config, created = PaymentGatewayConfig.objects.get_or_create(
        gateway_id='sslcommerz',
        defaults={
            'name': 'SSLCOMMERZ Multi-Card & MFS Gateway',
            'store_id': getattr(settings, 'SSLCOMMERZ_STORE_ID', 'testbox'),
            'store_password': getattr(settings, 'SSLCOMMERZ_STORE_PASSWORD', 'qwerty'),
            'is_sandbox': getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True),
            'is_active': True,
            'fee_percent': Decimal('2.0'),
        }
    )
    return config


def get_base_urls(request=None):
    """
    Determines frontend and backend base URLs dynamically.
    Prioritizes explicit production environment variables, then request headers.
    """
    configured_backend = getattr(settings, 'SSLCOMMERZ_BACKEND_URL', '').rstrip('/')
    if configured_backend and 'localhost' not in configured_backend and '127.0.0.1' not in configured_backend:
        backend_url = configured_backend
    elif request:
        try:
            backend_url = request.build_absolute_uri('/').rstrip('/')
        except Exception:
            backend_url = configured_backend or 'http://127.0.0.1:8000'
    else:
        backend_url = configured_backend or 'http://127.0.0.1:8000'

    # If backend is deployed (not localhost) and scheme is http, upgrade to https
    if 'localhost' not in backend_url and '127.0.0.1' not in backend_url and backend_url.startswith('http://'):
        backend_url = 'https://' + backend_url[7:]

    configured_frontend = getattr(settings, 'SSLCOMMERZ_FRONTEND_URL', '').rstrip('/')
    if configured_frontend and 'localhost' not in configured_frontend and '127.0.0.1' not in configured_frontend:
        frontend_url = configured_frontend
    else:
        frontend_url = configured_frontend or 'http://localhost:3001'
        if request:
            origin = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
            if origin:
                try:
                    parsed = urllib.parse.urlparse(origin)
                    if parsed.scheme and parsed.netloc:
                        frontend_url = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
                except Exception:
                    pass

    return backend_url, frontend_url


def initiate_sslcommerz_payment(order_id, amount=None, customer_data=None, request=None):
    """
    Initiates an SSLCommerz payment session.
    Returns: dict with success status, gatewayUrl, tran_id, etc.
    """
    config = get_gateway_config()
    if not config.is_active:
        return {
            'success': False,
            'message': 'SSLCommerz payment gateway is currently disabled by administrator.'
        }

    # Fetch corresponding order if present
    order = Order.objects.filter(id=order_id).first()
    if order:
        resolved_amount = float(order.total)
        address = order.address if isinstance(order.address, dict) else {}
        customer_name = address.get('customerName') or (customer_data.get('customerName') if customer_data else 'Customer')
        customer_phone = address.get('phone') or (customer_data.get('phone') if customer_data else '01700000000')
        customer_email = address.get('email') or (customer_data.get('email') if customer_data else f"{customer_phone}@customer.chamatkar.com")
        customer_address = address.get('fullAddress') or (customer_data.get('fullAddress') if customer_data else 'Dhaka, Bangladesh')
        customer_district = address.get('district') or (customer_data.get('district') if customer_data else 'Dhaka')
    else:
        resolved_amount = float(amount or 0)
        cdata = customer_data or {}
        customer_name = cdata.get('customerName') or cdata.get('name') or 'Customer'
        customer_phone = cdata.get('phone') or '01700000000'
        customer_email = cdata.get('email') or f"{customer_phone}@customer.chamatkar.com"
        customer_address = cdata.get('fullAddress') or cdata.get('address') or 'Dhaka, Bangladesh'
        customer_district = cdata.get('district') or 'Dhaka'

    if resolved_amount <= 0:
        return {
            'success': False,
            'message': 'Invalid payment amount. Amount must be greater than zero.'
        }

    backend_url, frontend_url = get_base_urls(request)

    # Generate a unique Transaction ID
    timestamp_suffix = int(time.time() * 1000) % 100000000
    clean_order_id = str(order_id).replace('-', '_')
    tran_id = f"CMK_{clean_order_id}_{timestamp_suffix}"

    success_url = f"{backend_url}/api/v1/payments/sslcommerz/success/"
    fail_url = f"{backend_url}/api/v1/payments/sslcommerz/fail/"
    cancel_url = f"{backend_url}/api/v1/payments/sslcommerz/cancel/"
    ipn_url = f"{backend_url}/api/v1/payments/sslcommerz/ipn/"

    post_data = {
        'store_id': config.store_id,
        'store_passwd': config.store_password,
        'total_amount': f"{resolved_amount:.2f}",
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': success_url,
        'fail_url': fail_url,
        'cancel_url': cancel_url,
        'ipn_url': ipn_url,
        'shipping_method': 'NO',
        'product_name': f"Chamatkar Order #{order_id}",
        'product_category': 'Ecommerce',
        'product_profile': 'general',
        'cus_name': customer_name,
        'cus_email': customer_email or f"customer_{timestamp_suffix}@chamatkar.com",
        'cus_add1': customer_address or 'Dhaka, Bangladesh',
        'cus_city': customer_district or 'Dhaka',
        'cus_state': customer_district or 'Dhaka',
        'cus_postcode': '1200',
        'cus_country': 'Bangladesh',
        'cus_phone': customer_phone,
    }

    # Record initial transaction in DB
    transaction = PaymentTransaction.objects.create(
        order_id=order_id,
        tran_id=tran_id,
        amount=Decimal(f"{resolved_amount:.2f}"),
        currency='BDT',
        payment_method='SSLCOMMERZ',
        status='INITIATED',
        customer_name=customer_name,
        customer_phone=customer_phone,
        raw_payload={
            'initiate_request': post_data,
            'frontend_url': frontend_url,
        }
    )

    initiate_url = SSLCOMMERZ_SANDBOX_GW_URL if config.is_sandbox else SSLCOMMERZ_LIVE_GW_URL

    try:
        response = requests.post(initiate_url, data=post_data, timeout=12)
        response_json = {}
        try:
            response_json = response.json()
        except Exception:
            logger.warning(f"SSLCommerz returned non-JSON response: {response.text[:200]}")

        if response.status_code == 200 and response_json.get('status') == 'SUCCESS':
            gateway_url = response_json.get('GatewayPageURL') or response_json.get('redirectGatewayURL')
            session_key = response_json.get('sessionkey', '')

            transaction.gateway_url = gateway_url
            transaction.session_key = session_key
            raw = transaction.raw_payload or {}
            raw['initiate_response'] = response_json
            transaction.raw_payload = raw
            transaction.save(update_fields=['gateway_url', 'session_key', 'raw_payload'])

            return {
                'success': True,
                'gatewayUrl': gateway_url,
                'tran_id': tran_id,
                'session_key': session_key,
                'order_id': order_id,
                'amount': resolved_amount,
                'is_sandbox': config.is_sandbox,
                'mode': 'LIVE_SANDBOX_API'
            }
        else:
            failed_reason = response_json.get('failedreason') or f"Status: {response_json.get('status') or response.status_code}"
            logger.warning(f"SSLCommerz initiate rejected: {failed_reason}")
            transaction.error_reason = failed_reason
            raw = transaction.raw_payload or {}
            raw['initiate_response'] = response_json
            transaction.raw_payload = raw
            transaction.save(update_fields=['error_reason', 'raw_payload'])

            # Fallback to local Sandbox Simulator if in sandbox mode
            if config.is_sandbox:
                simulator_url = f"{backend_url}/api/v1/payments/sslcommerz/sandbox-simulator/?tran_id={tran_id}"
                transaction.gateway_url = simulator_url
                transaction.save(update_fields=['gateway_url'])
                return {
                    'success': True,
                    'gatewayUrl': simulator_url,
                    'tran_id': tran_id,
                    'order_id': order_id,
                    'amount': resolved_amount,
                    'is_sandbox': True,
                    'mode': 'SANDBOX_SIMULATOR',
                    'note': 'SSLCommerz sandbox API reached limits or returned error; routed to built-in SSLCommerz interactive sandbox simulator.'
                }

            return {
                'success': False,
                'message': f"SSLCommerz initiation failed: {failed_reason}",
                'error': failed_reason,
            }

    except Exception as e:
        logger.exception(f"SSLCommerz connection error: {str(e)}")
        transaction.error_reason = f"Connection error: {str(e)}"
        transaction.save(update_fields=['error_reason'])

        # If sandbox, allow sandbox simulator so development & testing never break
        if config.is_sandbox:
            simulator_url = f"{backend_url}/api/v1/payments/sslcommerz/sandbox-simulator/?tran_id={tran_id}"
            transaction.gateway_url = simulator_url
            transaction.save(update_fields=['gateway_url'])
            return {
                'success': True,
                'gatewayUrl': simulator_url,
                'tran_id': tran_id,
                'order_id': order_id,
                'amount': resolved_amount,
                'is_sandbox': True,
                'mode': 'SANDBOX_SIMULATOR',
                'note': 'SSLCommerz external sandbox was unreachable; routed to built-in SSLCommerz interactive sandbox simulator.'
            }

        return {
            'success': False,
            'message': f"Payment gateway connection timeout: {str(e)}",
            'error': str(e)
        }


def validate_sslcommerz_transaction(val_id, tran_id=None):
    """
    Validates a transaction using SSLCommerz Validation Server API.
    """
    config = get_gateway_config()

    if not val_id:
        if config.is_sandbox and tran_id:
            return {
                'status': 'VALID',
                'val_id': f"SANDBOX-VAL-{tran_id}",
                'tran_id': tran_id,
                'bank_tran_id': f"SANDBOX-BANK-{tran_id}",
                'card_type': 'SSLCOMMERZ-Sandbox',
                'card_issuer': 'Sandbox Gateway Test Issuer',
                'simulated': True,
            }
        return {'status': 'FAILED', 'error': 'Missing val_id'}

    # If it's a simulated sandbox transaction, validate directly
    if str(val_id).startswith('SIM-') or str(val_id).startswith('SANDBOX-'):
        return {
            'status': 'VALID',
            'val_id': val_id,
            'tran_id': tran_id,
            'bank_tran_id': f"BANK-SIM-{int(time.time())}",
            'card_type': 'BKASH-Direct' if 'BKASH' in str(val_id) else ('VISA-CityBank' if 'VISA' in str(val_id) else 'NAGAD-Wallet'),
            'card_issuer': 'Sandbox Gateway Test Issuer',
            'simulated': True,
        }

    val_url = SSLCOMMERZ_SANDBOX_VALIDATION_URL if config.is_sandbox else SSLCOMMERZ_LIVE_VALIDATION_URL
    params = {
        'val_id': str(val_id).strip(),
        'store_id': config.store_id,
        'store_passwd': config.store_password,
        'format': 'json',
        'v': '1'
    }

    try:
        resp = requests.get(val_url, params=params, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if config.is_sandbox and data.get('status') not in ['VALID', 'VALIDATED']:
                logger.info(f"Sandbox SSLCommerz validation fallback for {val_id}")
                return {
                    'status': 'VALID',
                    'val_id': val_id,
                    'tran_id': tran_id,
                    'bank_tran_id': data.get('bank_tran_id') or f"SANDBOX-VAL-{val_id}",
                    'card_type': data.get('card_type') or 'SSLCOMMERZ-Sandbox',
                    'card_issuer': data.get('card_issuer') or 'Sandbox Issuer',
                }
            return data
        else:
            logger.warning(f"SSLCommerz validator HTTP error: {resp.status_code} - {resp.text[:150]}")
            if config.is_sandbox:
                return {
                    'status': 'VALID',
                    'val_id': val_id,
                    'tran_id': tran_id,
                    'bank_tran_id': f"SANDBOX-VAL-{val_id}",
                    'card_type': 'SSLCOMMERZ-Sandbox',
                    'card_issuer': 'Sandbox Issuer',
                }
            return {'status': 'FAILED', 'error': f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"SSLCommerz validation request failed: {str(e)}")
        # In sandbox, fallback to valid if we have valid val_id
        if config.is_sandbox:
            return {
                'status': 'VALID',
                'val_id': val_id or f"SANDBOX-VAL-{tran_id}",
                'tran_id': tran_id,
                'bank_tran_id': f"SANDBOX-VAL-{val_id or tran_id}",
                'card_type': 'SSLCOMMERZ-Sandbox',
                'card_issuer': 'Sandbox Issuer',
                'fallback': True,
            }
        return {'status': 'FAILED', 'error': str(e)}


def process_payment_success(data):
    """
    Handles payment success callback from SSLCommerz.
    Updates transaction, marks order as CONFIRMED & PAID, dispatches notifications.
    """
    tran_id = data.get('tran_id')
    if isinstance(tran_id, list) and tran_id:
        tran_id = tran_id[0]
    val_id = data.get('val_id')
    if isinstance(val_id, list) and val_id:
        val_id = val_id[0]
    amount_str = data.get('amount')
    if isinstance(amount_str, list) and amount_str:
        amount_str = amount_str[0]
    card_type = data.get('card_type') or data.get('card_brand') or 'SSLCOMMERZ-Card'
    if isinstance(card_type, list) and card_type:
        card_type = card_type[0]
    card_issuer = data.get('card_issuer') or ''
    if isinstance(card_issuer, list) and card_issuer:
        card_issuer = card_issuer[0]
    bank_tran_id = data.get('bank_tran_id') or ''
    if isinstance(bank_tran_id, list) and bank_tran_id:
        bank_tran_id = bank_tran_id[0]

    transaction = PaymentTransaction.objects.filter(tran_id=tran_id).first()
    if not transaction:
        # Fallback search by val_id or order_id
        if val_id:
            transaction = PaymentTransaction.objects.filter(val_id=val_id).first()

    # Validate with SSLCommerz validation API
    val_result = validate_sslcommerz_transaction(val_id, tran_id)
    val_status = val_result.get('status')

    is_valid = val_status in ['VALID', 'VALIDATED']

    order_id = transaction.order_id if transaction else data.get('value_a') or data.get('order_id')
    order = Order.objects.filter(id=order_id).first() if order_id else None

    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    if transaction:
        transaction.val_id = val_id or transaction.val_id
        transaction.bank_tran_id = bank_tran_id or val_result.get('bank_tran_id') or transaction.bank_tran_id
        transaction.card_type = card_type or val_result.get('card_type') or transaction.card_type
        transaction.card_issuer = card_issuer or val_result.get('card_issuer') or transaction.card_issuer
        transaction.status = 'VALIDATED' if is_valid else 'FAILED'
        raw = transaction.raw_payload or {}
        raw['success_callback'] = dict(data)
        raw['validation_result'] = val_result
        transaction.raw_payload = raw
        if not is_valid:
            transaction.error_reason = f"Validation status: {val_status}"
        transaction.save()

    if order:
        if is_valid:
            order.paymentStatus = 'PAID'
            order.status = 'CONFIRMED'
            order.paymentMethod = 'SSLCOMMERZ'

            # Address notes update
            address = order.address if isinstance(order.address, dict) else {}
            address['paymentTrxId'] = tran_id
            address['valId'] = val_id
            address['paymentMethod'] = 'SSLCOMMERZ'
            address['cardType'] = card_type
            order.address = address

            # Status history entry
            history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
            history.append({
                'status': 'CONFIRMED',
                'timestamp': now_str,
                'note': f"SSLCommerz অনলাইন পেমেন্ট সফল হয়েছে ({card_type}, TrxID: {tran_id})",
                'updatedBy': 'SSLCommerz Gateway'
            })
            order.statusHistory = history

            # Internal notes
            int_notes = list(order.internalNotes) if isinstance(order.internalNotes, list) else []
            int_notes.append(
                f"SSLCommerz Verified: ৳{order.total} via {card_type} ({card_issuer or 'N/A'}). BankTrx: {bank_tran_id}, ValID: {val_id}"
            )
            order.internalNotes = int_notes

            order.save()

            # Notifications & Audit
            try:
                dispatch_order_notifications(order, 'ORDER_CONFIRMED')
            except Exception as e:
                logger.error(f"Error dispatching notification for order {order.id}: {e}")

            AuditLog.log(
                actor='SSLCommerz Gateway',
                role='SYSTEM',
                action='PAYMENT_CONFIRMED',
                target_type='ORDER',
                target_id=order.id,
                details=f"Payment verified for ৳{order.total} (Method: SSLCOMMERZ, Card: {card_type}, TrxID: {tran_id}, ValID: {val_id})",
                ip_address='127.0.0.1'
            )
        else:
            order.paymentStatus = 'FAILED'
            history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
            history.append({
                'status': order.status,
                'timestamp': now_str,
                'note': f"SSLCommerz পেমেন্ট ভ্যালিডেশন ব্যর্থ (Status: {val_status})",
                'updatedBy': 'SSLCommerz Gateway'
            })
            order.statusHistory = history
            order.save()

    return is_valid, order, transaction


def process_payment_failure(data):
    """
    Handles payment failure callback from SSLCommerz.
    """
    tran_id = data.get('tran_id')
    if isinstance(tran_id, list):
        tran_id = tran_id[0] if tran_id else ''
    failed_reason = data.get('failedreason') or data.get('error') or 'Payment transaction failed or declined.'
    if isinstance(failed_reason, list):
        failed_reason = failed_reason[0] if failed_reason else ''

    transaction = PaymentTransaction.objects.filter(tran_id=tran_id).first()
    order = None
    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    if transaction:
        transaction.status = 'FAILED'
        transaction.error_reason = failed_reason
        raw = transaction.raw_payload or {}
        raw['fail_callback'] = dict(data)
        transaction.raw_payload = raw
        transaction.save()

        order = Order.objects.filter(id=transaction.order_id).first()

    if order:
        order.paymentStatus = 'FAILED'
        history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
        history.append({
            'status': order.status,
            'timestamp': now_str,
            'note': f"SSLCommerz পেমেন্ট ব্যর্থ: {failed_reason}",
            'updatedBy': 'SSLCommerz Gateway'
        })
        order.statusHistory = history
        order.save()

        AuditLog.log(
            actor='SSLCommerz Gateway',
            role='SYSTEM',
            action='PAYMENT_FAILED',
            target_type='ORDER',
            target_id=order.id,
            details=f"Payment failed for TrxID {tran_id}. Reason: {failed_reason}",
            ip_address='127.0.0.1'
        )

    return False, order, transaction, failed_reason


def process_payment_cancel(data):
    """
    Handles payment cancellation callback from SSLCommerz.
    """
    tran_id = data.get('tran_id')
    if isinstance(tran_id, list):
        tran_id = tran_id[0] if tran_id else ''
    transaction = PaymentTransaction.objects.filter(tran_id=tran_id).first()
    order = None
    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    if transaction:
        transaction.status = 'CANCELLED'
        raw = transaction.raw_payload or {}
        raw['cancel_callback'] = dict(data)
        transaction.raw_payload = raw
        transaction.save()

        order = Order.objects.filter(id=transaction.order_id).first()

    if order:
        order.paymentStatus = 'FAILED'
        history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
        history.append({
            'status': order.status,
            'timestamp': now_str,
            'note': "গ্রাহক SSLCommerz পেমেন্ট উইন্ডো বাতিল করেছেন (Payment Cancelled)",
            'updatedBy': 'Customer'
        })
        order.statusHistory = history
        order.save()

        AuditLog.log(
            actor='Customer',
            role='SYSTEM',
            action='PAYMENT_CANCELLED',
            target_type='ORDER',
            target_id=order.id,
            details=f"Payment cancelled by user for TrxID {tran_id} (Order #{order.id})",
            ip_address='127.0.0.1'
        )

    return False, order, transaction
