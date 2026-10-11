import json
import logging
import urllib.parse
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from .models import PaymentTransaction, PaymentGatewayConfig, PaymentMethodSetting
from .serializers import PaymentTransactionSerializer, PaymentGatewayConfigSerializer, PaymentMethodSettingSerializer
from .services import (
    get_gateway_config,
    get_or_seed_payment_methods,
    get_base_urls,
    initiate_sslcommerz_payment,
    validate_sslcommerz_transaction,
    process_payment_success,
    process_payment_failure,
    process_payment_cancel,
)
from order.models import Order

logger = logging.getLogger(__name__)


def _extract_request_data(request):
    """
    Extracts data safely whether request is form POST, query GET or JSON.
    Flattens any single-item lists created by Django QueryDict.
    """
    raw = {}
    if request.method == 'GET':
        raw = request.GET.dict()
    elif hasattr(request, 'data') and request.data:
        if hasattr(request.data, 'dict'):
            raw = request.data.dict()
        elif isinstance(request.data, dict):
            raw = dict(request.data)
        else:
            try:
                raw = dict(request.data)
            except Exception:
                raw = {}
    elif request.POST:
        raw = request.POST.dict()
    else:
        try:
            if request.body:
                raw = json.loads(request.body)
        except Exception:
            raw = {}

    cleaned = {}
    for k, v in raw.items():
        if isinstance(v, list) and len(v) == 1:
            cleaned[k] = v[0]
        elif isinstance(v, list) and len(v) == 0:
            cleaned[k] = ''
        else:
            cleaned[k] = v
    return cleaned


@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_payment_view(request):
    """
    POST /api/v1/payments/initiate
    Initiates payment session with SSLCommerz and returns GatewayPageURL.
    """
    data = request.data
    order_id = data.get('orderId') or data.get('order_id')
    amount = data.get('amount')
    customer_data = data.get('customerData') or data.get('address') or {
        'customerName': data.get('customerName') or data.get('name'),
        'phone': data.get('phone') or data.get('customerPhone'),
        'email': data.get('email'),
        'fullAddress': data.get('fullAddress') or data.get('address'),
        'district': data.get('district'),
    }

    if not order_id:
        return Response({
            'success': False,
            'message': 'Order ID is required to initiate payment'
        }, status=status.HTTP_400_BAD_REQUEST)

    result = initiate_sslcommerz_payment(
        order_id=order_id,
        amount=amount,
        customer_data=customer_data,
        request=request
    )

    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


def _render_redirect_page(target_url, title, status_text, is_success=True):
    """
    Renders an HTML interstitial page that auto-redirects the browser cleanly.
    """
    color = "#059669" if is_success else "#dc2626"
    icon = "✓" if is_success else "✕"
    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - AmarDokan</title>
    <meta http-equiv="refresh" content="1;url={target_url}">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 24px;
            padding: 40px 32px;
            max-width: 480px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }}
        .icon-circle {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: {color}15;
            color: {color};
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: bold;
            margin: 0 auto 20px auto;
        }}
        h2 {{ color: #0f172a; font-size: 20px; margin-bottom: 8px; font-weight: 800; }}
        p {{ color: #64748b; font-size: 14px; margin-bottom: 24px; line-height: 1.5; }}
        .btn {{
            display: inline-block;
            background: {color};
            color: white;
            text-decoration: none;
            padding: 12px 28px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .spinner {{
            border: 3px solid #e2e8f0;
            border-top: 3px solid {color};
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 0.8s linear infinite;
            margin: 16px auto 0 auto;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-circle">{icon}</div>
        <h2>{title}</h2>
        <p>{status_text}<br>স্বয়ংক্রিয়ভাবে রিডাইরেক্ট করা হচ্ছে...</p>
        <a href="{target_url}" class="btn">তাৎক্ষণিক ফিরে যান →</a>
        <div class="spinner"></div>
    </div>
    <script>
        setTimeout(function() {{
            window.location.href = "{target_url}";
        }}, 800);
    </script>
</body>
</html>"""
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def sslcommerz_success_listener(request):
    """
    POST/GET /api/v1/payments/sslcommerz/success/
    Callback from SSLCommerz upon successful payment.
    Validates transaction and redirects user to frontend.
    """
    data = _extract_request_data(request)
    backend_url, frontend_url = get_base_urls(request)

    is_valid, order, transaction = process_payment_success(data)

    if transaction and isinstance(transaction.raw_payload, dict):
        saved_frontend = transaction.raw_payload.get('frontend_url')
        if saved_frontend and ('localhost' in frontend_url or '127.0.0.1' in frontend_url):
            frontend_url = saved_frontend.rstrip('/')

    order_id = order.id if order else (transaction.order_id if transaction else data.get('tran_id', 'UNKNOWN'))
    tran_id = data.get('tran_id', '')
    val_id = data.get('val_id', '')

    target_url = f"{frontend_url}/?order_id={urllib.parse.quote(str(order_id))}&payment_status=success&tran_id={urllib.parse.quote(str(tran_id))}&val_id={urllib.parse.quote(str(val_id))}"

    if is_valid:
        return _render_redirect_page(
            target_url=target_url,
            title="পেমেন্ট সফল হয়েছে!",
            status_text="আপনার SSLCommerz অনলাইন পেমেন্ট সফলভাবে যাচাই হয়েছে।",
            is_success=True
        )
    else:
        fail_url = f"{frontend_url}/?order_id={urllib.parse.quote(str(order_id))}&payment_status=failed&reason=Validation+Failed"
        return _render_redirect_page(
            target_url=fail_url,
            title="পেমেন্ট ভ্যালিডেশন ব্যর্থ",
            status_text="পেমেন্ট গেটওয়ে ট্রানজ্যাকশনটি নিশ্চিত করতে পারেনি।",
            is_success=False
        )


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def sslcommerz_fail_listener(request):
    """
    POST/GET /api/v1/payments/sslcommerz/fail/
    Callback from SSLCommerz upon failed payment.
    """
    data = _extract_request_data(request)
    backend_url, frontend_url = get_base_urls(request)

    is_success, order, transaction, reason = process_payment_failure(data)

    if transaction and isinstance(transaction.raw_payload, dict):
        saved_frontend = transaction.raw_payload.get('frontend_url')
        if saved_frontend and ('localhost' in frontend_url or '127.0.0.1' in frontend_url):
            frontend_url = saved_frontend.rstrip('/')

    order_id = order.id if order else (transaction.order_id if transaction else data.get('tran_id', 'UNKNOWN'))
    tran_id = data.get('tran_id', '')

    target_url = f"{frontend_url}/?order_id={urllib.parse.quote(str(order_id))}&payment_status=failed&reason={urllib.parse.quote(str(reason))}&tran_id={urllib.parse.quote(str(tran_id))}"

    return _render_redirect_page(
        target_url=target_url,
        title="পেমেন্ট ব্যর্থ হয়েছে",
        status_text=f"কার্ড বা অ্যাকাউন্ট থেকে পেমেন্ট সম্পন্ন হয়নি: {reason}",
        is_success=False
    )


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def sslcommerz_cancel_listener(request):
    """
    POST/GET /api/v1/payments/sslcommerz/cancel/
    Callback from SSLCommerz when user cancels payment.
    """
    data = _extract_request_data(request)
    backend_url, frontend_url = get_base_urls(request)

    is_success, order, transaction = process_payment_cancel(data)

    if transaction and isinstance(transaction.raw_payload, dict):
        saved_frontend = transaction.raw_payload.get('frontend_url')
        if saved_frontend and ('localhost' in frontend_url or '127.0.0.1' in frontend_url):
            frontend_url = saved_frontend.rstrip('/')

    order_id = order.id if order else (transaction.order_id if transaction else data.get('tran_id', 'UNKNOWN'))
    tran_id = data.get('tran_id', '')

    target_url = f"{frontend_url}/?order_id={urllib.parse.quote(str(order_id))}&payment_status=cancelled&tran_id={urllib.parse.quote(str(tran_id))}"

    return _render_redirect_page(
        target_url=target_url,
        title="পেমেন্ট বাতিল করা হয়েছে",
        status_text="আপনি SSLCommerz পেমেন্ট উইন্ডো বাতিল করেছেন।",
        is_success=False
    )


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def sslcommerz_ipn_listener(request):
    """
    POST /api/v1/payments/sslcommerz/ipn/
    Instant Payment Notification (IPN) webhook from SSLCommerz.
    """
    data = _extract_request_data(request)
    status_val = data.get('status')
    tran_id = data.get('tran_id')

    logger.info(f"SSLCommerz IPN received for {tran_id}: status={status_val}")

    if status_val in ['VALID', 'VALIDATED']:
        is_valid, order, transaction = process_payment_success(data)
        return Response({
            'success': is_valid,
            'message': 'IPN verified and order confirmed',
            'order_id': order.id if order else None
        }, status=status.HTTP_200_OK)
    elif status_val == 'FAILED':
        process_payment_failure(data)
        return Response({'success': False, 'message': 'IPN failed status recorded'}, status=status.HTTP_200_OK)
    elif status_val == 'CANCELLED':
        process_payment_cancel(data)
        return Response({'success': False, 'message': 'IPN cancelled status recorded'}, status=status.HTTP_200_OK)

    return Response({'success': True, 'message': 'IPN received'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def sandbox_simulator_view(request):
    """
    GET /api/v1/payments/sslcommerz/sandbox-simulator/
    Interactive Sandbox Simulator to test SSLCommerz payment options locally.
    """
    tran_id = request.GET.get('tran_id', '')
    transaction = PaymentTransaction.objects.filter(tran_id=tran_id).first()

    order = Order.objects.filter(id=transaction.order_id).first() if transaction else None
    order_id = transaction.order_id if transaction else 'UNKNOWN'
    amount = float(transaction.amount) if transaction else 0.0
    customer_name = transaction.customer_name if transaction else 'Customer'

    backend_url, frontend_url = get_base_urls(request)
    success_callback = f"{backend_url}/api/v1/payments/sslcommerz/success/"
    fail_callback = f"{backend_url}/api/v1/payments/sslcommerz/fail/"
    cancel_callback = f"{backend_url}/api/v1/payments/sslcommerz/cancel/"

    sim_val_id = f"SIM-{tran_id}-{int(time.time() * 1000) % 100000}"

    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSLCOMMERZ Sandbox Gateway Simulator - AmarDokan</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            max-width: 520px;
            width: 100%;
            background: #1e293b;
            border-radius: 24px;
            border: 1px solid #334155;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            padding: 24px;
            color: white;
            text-align: center;
        }}
        .badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .amount-display {{
            font-size: 32px;
            font-weight: 900;
            margin: 6px 0;
        }}
        .order-info {{
            font-size: 12px;
            opacity: 0.9;
        }}
        .content {{
            padding: 24px;
        }}
        .channel-title {{
            font-size: 13px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
        }}
        .channel-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .channel-btn {{
            background: #334155;
            border: 1px solid #475569;
            border-radius: 14px;
            padding: 14px 12px;
            color: white;
            cursor: pointer;
            text-align: left;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            width: 100%;
        }}
        .channel-btn:hover {{
            background: #475569;
            border-color: #38bdf8;
            transform: translateY(-2px);
        }}
        .channel-btn.bkash:hover {{ border-color: #e2136e; background: #e2136e15; }}
        .channel-btn.nagad:hover {{ border-color: #f7941d; background: #f7941d15; }}
        .channel-btn.card:hover {{ border-color: #0284c7; background: #0284c715; }}
        .channel-btn.rocket:hover {{ border-color: #8c3494; background: #8c349415; }}
        .channel-icon {{
            font-size: 20px;
            flex-shrink: 0;
        }}
        .channel-name {{
            font-weight: 700;
            font-size: 13px;
            display: block;
        }}
        .channel-sub {{
            font-size: 10px;
            color: #94a3b8;
        }}
        .actions-row {{
            border-top: 1px solid #334155;
            padding-top: 16px;
            display: flex;
            gap: 10px;
        }}
        .btn-fail, .btn-cancel {{
            flex: 1;
            padding: 10px;
            border-radius: 12px;
            border: none;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .btn-fail {{ background: #dc2626; color: white; }}
        .btn-cancel {{ background: #475569; color: #cbd5e1; }}
        .btn-fail:hover, .btn-cancel:hover {{ opacity: 0.9; }}
        .footer-note {{
            font-size: 11px;
            color: #64748b;
            text-align: center;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="badge">SSLCOMMERZ Sandbox Gateway</div>
            <div class="amount-display">৳{amount:,.2f}</div>
            <div class="order-info">Order #{order_id} &bull; TrxID: {tran_id}</div>
        </div>
        <div class="content">
            <div class="channel-title">Select Test Payment Channel</div>
            <div class="channel-grid">
                <!-- bKash Simulation -->
                <form action="{success_callback}" method="POST">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <input type="hidden" name="val_id" value="{sim_val_id}_BKASH">
                    <input type="hidden" name="amount" value="{amount}">
                    <input type="hidden" name="card_type" value="BKASH-Direct">
                    <input type="hidden" name="card_issuer" value="bKash Limited">
                    <input type="hidden" name="bank_tran_id" value="BKTRX{int(time.time())}">
                    <input type="hidden" name="status" value="VALID">
                    <button type="submit" class="channel-btn bkash">
                        <span class="channel-icon">📱</span>
                        <div>
                            <span class="channel-name">bKash PGW</span>
                            <span class="channel-sub">Instant Sandbox</span>
                        </div>
                    </button>
                </form>

                <!-- Nagad Simulation -->
                <form action="{success_callback}" method="POST">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <input type="hidden" name="val_id" value="{sim_val_id}_NAGAD">
                    <input type="hidden" name="amount" value="{amount}">
                    <input type="hidden" name="card_type" value="NAGAD-Wallet">
                    <input type="hidden" name="card_issuer" value="Nagad Digital">
                    <input type="hidden" name="bank_tran_id" value="NGDTRX{int(time.time())}">
                    <input type="hidden" name="status" value="VALID">
                    <button type="submit" class="channel-btn nagad">
                        <span class="channel-icon">⚡</span>
                        <div>
                            <span class="channel-name">Nagad</span>
                            <span class="channel-sub">Direct MFS</span>
                        </div>
                    </button>
                </form>

                <!-- Visa / Mastercard Simulation -->
                <form action="{success_callback}" method="POST">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <input type="hidden" name="val_id" value="{sim_val_id}_VISA">
                    <input type="hidden" name="amount" value="{amount}">
                    <input type="hidden" name="card_type" value="VISA-CityBank">
                    <input type="hidden" name="card_issuer" value="City Bank Ltd">
                    <input type="hidden" name="bank_tran_id" value="VSTRX{int(time.time())}">
                    <input type="hidden" name="status" value="VALID">
                    <button type="submit" class="channel-btn card">
                        <span class="channel-icon">💳</span>
                        <div>
                            <span class="channel-name">Visa / Master</span>
                            <span class="channel-sub">Credit/Debit Card</span>
                        </div>
                    </button>
                </form>

                <!-- Rocket DBBL Simulation -->
                <form action="{success_callback}" method="POST">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <input type="hidden" name="val_id" value="{sim_val_id}_ROCKET">
                    <input type="hidden" name="amount" value="{amount}">
                    <input type="hidden" name="card_type" value="DBBL-Nexus">
                    <input type="hidden" name="card_issuer" value="Dutch Bangla Bank">
                    <input type="hidden" name="bank_tran_id" value="DBBLTRX{int(time.time())}">
                    <input type="hidden" name="status" value="VALID">
                    <button type="submit" class="channel-btn rocket">
                        <span class="channel-icon">🏦</span>
                        <div>
                            <span class="channel-name">DBBL / Rocket</span>
                            <span class="channel-sub">Nexus & Banking</span>
                        </div>
                    </button>
                </form>
            </div>

            <div class="actions-row">
                <!-- Fail Test -->
                <form action="{fail_callback}" method="POST" style="flex: 1;">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <input type="hidden" name="failedreason" value="Card Insufficient Balance (Test Simulation)">
                    <button type="submit" class="btn-fail" style="width: 100%;">
                        ✕ Simulate Failure
                    </button>
                </form>

                <!-- Cancel Test -->
                <form action="{cancel_callback}" method="POST" style="flex: 1;">
                    <input type="hidden" name="tran_id" value="{tran_id}">
                    <button type="submit" class="btn-cancel" style="width: 100%;">
                        ⊘ Cancel Payment
                    </button>
                </form>
            </div>

            <div class="footer-note">
                SSLCOMMERZ Multi-Card Sandbox Environment &bull; AmarDokan E-Commerce Platform
            </div>
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_transactions_list(request):
    """
    GET /api/v1/payments/transactions
    Returns paginated/filtered list of all PaymentTransactions for Admin panel.
    """
    status_filter = request.query_params.get('status')
    search = request.query_params.get('search')
    order_id = request.query_params.get('order_id')

    queryset = PaymentTransaction.objects.all().order_by('-created_at')

    if status_filter and status_filter != 'ALL':
        queryset = queryset.filter(status=status_filter)

    if order_id:
        queryset = queryset.filter(order_id__icontains=order_id)

    if search:
        s = search.strip()
        queryset = queryset.filter(
            models.Q(tran_id__icontains=s) |
            models.Q(val_id__icontains=s) |
            models.Q(order_id__icontains=s) |
            models.Q(customer_phone__icontains=s) |
            models.Q(customer_name__icontains=s) |
            models.Q(bank_tran_id__icontains=s)
        )

    serializer = PaymentTransactionSerializer(queryset[:100], many=True)
    return Response({
        'success': True,
        'count': queryset.count(),
        'transactions': serializer.data
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_config_view(request):
    """
    GET/POST /api/v1/payments/config
    Retrieves or updates SSLCommerz configuration.
    """
    config = get_gateway_config()

    if request.method == 'POST':
        data = request.data
        if 'store_id' in data:
            config.store_id = str(data['store_id']).strip()
        if 'store_password' in data:
            config.store_password = str(data['store_password']).strip()
        if 'is_sandbox' in data:
            config.is_sandbox = bool(data['is_sandbox'])
        if 'is_active' in data:
            config.is_active = bool(data['is_active'])
        if 'fee_percent' in data:
            try:
                config.fee_percent = float(data['fee_percent'])
            except Exception:
                pass
        config.save()

    serializer = PaymentGatewayConfigSerializer(config)
    return Response({
        'success': True,
        'config': serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_verify_view(request):
    """
    POST /api/v1/payments/verify
    Manually verifies or syncs a transaction with SSLCommerz.
    """
    tran_id = request.data.get('tran_id')
    val_id = request.data.get('val_id')

    transaction = None
    if tran_id:
        transaction = PaymentTransaction.objects.filter(tran_id=tran_id).first()
    elif val_id:
        transaction = PaymentTransaction.objects.filter(val_id=val_id).first()

    if not transaction:
        return Response({
            'success': False,
            'message': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)

    effective_val_id = val_id or transaction.val_id
    if not effective_val_id:
        config = get_gateway_config()
        if config.is_sandbox:
            effective_val_id = f"SANDBOX-VAL-{transaction.tran_id}"
        else:
            return Response({
                'success': False,
                'message': 'Validation ID (val_id) is missing for this transaction'
            }, status=status.HTTP_400_BAD_REQUEST)

    val_result = validate_sslcommerz_transaction(effective_val_id, transaction.tran_id)

    if val_result.get('status') in ['VALID', 'VALIDATED']:
        payload = {
            'tran_id': transaction.tran_id,
            'val_id': effective_val_id,
            'amount': str(transaction.amount),
            'card_type': val_result.get('card_type') or transaction.card_type,
            'card_issuer': val_result.get('card_issuer') or transaction.card_issuer,
            'bank_tran_id': val_result.get('bank_tran_id') or transaction.bank_tran_id,
        }
        process_payment_success(payload)
        transaction.refresh_from_db()

        return Response({
            'success': True,
            'message': 'Transaction verified and marked as VALIDATED/PAID',
            'transaction': PaymentTransactionSerializer(transaction).data,
            'validation': val_result
        })
    else:
        return Response({
            'success': False,
            'message': f"Validation check returned: {val_result.get('status')}",
            'validation': val_result
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_methods_view(request):
    """
    GET/POST /api/v1/payments/methods
    GET: Returns list of all payment methods and their configs (seeds defaults if empty).
    POST: Updates configuration for one or multiple payment methods.
    """
    if request.method == 'POST':
        data = request.data
        if isinstance(data, list):
            for item in data:
                m_id = item.get('method_id')
                if m_id:
                    method = PaymentMethodSetting.objects.filter(method_id=m_id).first()
                    if method:
                        if 'is_active' in item:
                            method.is_active = bool(item['is_active'])
                        if 'name' in item:
                            method.name = str(item['name']).strip()
                        if 'account_type' in item:
                            method.account_type = str(item['account_type']).strip().upper()
                        if 'number' in item:
                            method.number = str(item['number']).strip()
                        if 'counter' in item:
                            method.counter = str(item['counter']).strip()
                        if 'instructions' in item:
                            method.instructions = str(item['instructions']).strip()
                        if 'display_order' in item:
                            try:
                                method.display_order = int(item['display_order'])
                            except Exception:
                                pass
                        method.save()
        elif isinstance(data, dict):
            m_id = data.get('method_id')
            if m_id:
                method = PaymentMethodSetting.objects.filter(method_id=m_id).first()
                if method:
                    if 'is_active' in data:
                        method.is_active = bool(data['is_active'])
                    if 'name' in data:
                        method.name = str(data['name']).strip()
                    if 'account_type' in data:
                        method.account_type = str(data['account_type']).strip().upper()
                    if 'number' in data:
                        method.number = str(data['number']).strip()
                    if 'counter' in data:
                        method.counter = str(data['counter']).strip()
                    if 'instructions' in data:
                        method.instructions = str(data['instructions']).strip()
                    if 'display_order' in data:
                        try:
                            method.display_order = int(data['display_order'])
                        except Exception:
                            pass
                    method.save()

    methods = get_or_seed_payment_methods()
    serializer = PaymentMethodSettingSerializer(methods, many=True)
    return Response({
        'success': True,
        'methods': serializer.data
    })
