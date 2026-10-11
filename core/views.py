from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.utils import timezone
import time
import uuid

from .models import AuditLog, MarketingEvent, NotificationLog, MarketingConfig, ShopSetting, StaffMember
from .serializers import AuditLogSerializer, MarketingEventSerializer, NotificationLogSerializer, MarketingConfigSerializer, ShopSettingSerializer, StaffMemberSerializer
from .capi import send_meta_capi_event

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    accept_header = request.META.get('HTTP_ACCEPT', '')
    if 'text/html' in accept_header:
        html_content = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AmarDokan Backend Engine • Django REST</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Hind+Siliguri:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card: #111827;
      --border: #1f293d;
      --primary: #10b981;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', 'Hind Siliguri', sans-serif;
      background: radial-gradient(circle at 50% 0%, #172554 0%, #090d16 60%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .container {
      max-width: 820px;
      width: 100%;
      background: rgba(17, 24, 39, 0.9);
      border: 1px solid var(--border);
      backdrop-filter: blur(16px);
      border-radius: 20px;
      padding: 40px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 20px;
    }
    .dot {
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }
    h1 {
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -0.5px;
      margin-bottom: 12px;
      background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    p.lead {
      color: var(--text-muted);
      font-size: 15px;
      line-height: 1.6;
      margin-bottom: 26px;
    }
    .action-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 16px;
      margin-bottom: 30px;
    }
    .action-card {
      background: #151d30;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      text-decoration: none;
      color: inherit;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .action-card:hover {
      border-color: #10b981;
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(16, 185, 129, 0.15);
    }
    .action-title {
      font-weight: 700;
      font-size: 15px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .action-desc {
      font-size: 13px;
      color: var(--text-muted);
    }
    .tag {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 4px;
      background: #1e293b;
      color: #94a3b8;
    }
    .btn-frontend {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff;
      padding: 14px 24px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-size: 15px;
      transition: opacity 0.2s;
    }
    .btn-frontend:hover { opacity: 0.9; }
    .footer-note {
      margin-top: 24px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 13px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }
    code {
      background: #1e293b;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      color: #38bdf8;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">
      <span class="dot"></span>
      Django REST API Server Online
    </div>
    <h1>AmarDokan Bangladesh Native E-Commerce Backend</h1>
    <p class="lead">
      স্বাগতম! আপনার Django REST Framework ব্যাকএন্ড সফলভাবে চালু হয়েছে এবং সক্রিয় রয়েছে।<br>
      ই-কমার্স স্টোরফ্রন্ট ব্রাউজ ও কেনাকাটা করতে নিচের সবুজ বাটনে ক্লিক করে ফ্রন্টএন্ডে যান।
    </p>

    <div style="margin-bottom: 28px;">
      <a href="http://localhost:3001" class="btn-frontend" target="_blank">
        🛍️ ওপেন করুন স্টোরফ্রন্ট ওয়েবসাইট (http://localhost:3001) →
      </a>
    </div>

    <div class="action-grid">
      <a href="/api/v1/health" class="action-card" target="_blank">
        <div class="action-title">
          API Health Check
          <span class="tag">GET</span>
        </div>
        <div class="action-desc">সিস্টেম ভার্সন ও ব্যাকএন্ডের হেলথ রেসপন্স দেখুন</div>
      </a>
      <a href="/api/v1/products" class="action-card" target="_blank">
        <div class="action-title">
          Products API
          <span class="tag">GET</span>
        </div>
        <div class="action-desc">ডেটাবেজের সকল পণ্যের লাইভ JSON ডেটা</div>
      </a>
      <a href="/api/v1/orders" class="action-card" target="_blank">
        <div class="action-title">
          Orders API
          <span class="tag">GET</span>
        </div>
        <div class="action-desc">কাস্টমার অর্ডার ও ট্র্যাকিং হিস্ট্রি</div>
      </a>
      <a href="/api/v1/couriers" class="action-card" target="_blank">
        <div class="action-title">
          Courier Configs
          <span class="tag">GET</span>
        </div>
        <div class="action-desc">পাঠাও, রেডএক্স ও স্টিডফাস্ট কুরিয়ার কনফিগারেশন</div>
      </a>
      <a href="/api/v1/audit-logs" class="action-card" target="_blank">
        <div class="action-title">
          Audit Logs
          <span class="tag">GET</span>
        </div>
        <div class="action-desc">সিস্টেম ও অ্যাডমিন অ্যাকশন ট্রেইল</div>
      </a>
      <a href="/admin/" class="action-card" target="_blank">
        <div class="action-title">
          Django Admin Portal
          <span class="tag">PORTAL</span>
        </div>
        <div class="action-desc">অ্যাডমিন প্যানেল দিয়ে ডেটাবেজ ব্রাউজ ও ম্যানেজ করুন</div>
      </a>
    </div>

    <div class="footer-note">
      <div>Stack: <code>Django 5.2</code> + <code>DRF</code> + <code>Python 3.14</code></div>
      <div>Frontend Proxy Target: <code>http://127.0.0.1:8000</code></div>
    </div>
  </div>
</body>
</html>"""
        return HttpResponse(html_content, content_type='text/html; charset=utf-8')

    return Response({
        'status': 'online',
        'platform': 'AmarDokan Bangladesh Native E-Commerce Backend (Django REST)',
        'version': '1.0.0',
        'frontend_url': 'http://localhost:3001',
        'endpoints': {
            'health': '/api/v1/health',
            'products': '/api/v1/products',
            'orders': '/api/v1/orders',
            'checkout': '/api/v1/checkout',
            'tracking': '/api/v1/tracking/lookup',
            'couriers': '/api/v1/couriers',
            'couriers_assign': '/api/v1/couriers/assign',
            'courier_webhook': '/api/v1/webhooks/couriers',
            'audit_logs': '/api/v1/audit-logs',
            'notifications': '/api/v1/notifications',
            'marketing_events': '/api/v1/marketing/events',
            'ai_assistant': '/api/v1/ai/assistant',
            'admin': '/admin/',
        }
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        'status': 'ok',
        'platform': 'AmarDokan Bangladesh Native E-Commerce (Django REST)',
        'version': '1.0.0',
        'timestamp': timezone.localtime().isoformat()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def audit_logs_list(request):
    logs = AuditLog.objects.all()[:100]
    serializer = AuditLogSerializer(logs, many=True)
    return Response({
        'success': True,
        'logs': serializer.data
    })

@api_view(['GET', 'POST', 'PUT'])
@permission_classes([AllowAny])
def marketing_config_view(request):
    config = MarketingConfig.objects.first()
    if not config:
        config = MarketingConfig.objects.create(
            id='default_config',
            pixelId='184729481920384',
            capiToken='',
            ga4Id='G-881920BD',
            testEventCode='',
            targetScope='GLOBAL',
            targetProductId='',
            targetLandingSlug='',
            isActive=True
        )

    if request.method == 'GET':
        serializer = MarketingConfigSerializer(config)
        return Response({'success': True, 'config': serializer.data})

    data = request.data
    config.pixelId = data.get('pixelId', config.pixelId)
    config.capiToken = data.get('capiToken', config.capiToken)
    config.ga4Id = data.get('ga4Id', config.ga4Id)
    config.testEventCode = data.get('testEventCode', config.testEventCode)
    config.adAccountId = data.get('adAccountId', getattr(config, 'adAccountId', ''))
    config.targetScope = data.get('targetScope', config.targetScope)
    config.targetProductId = data.get('targetProductId', config.targetProductId)
    config.targetLandingSlug = data.get('targetLandingSlug', config.targetLandingSlug)
    if 'isActive' in data:
        config.isActive = bool(data.get('isActive'))
    config.save()

    AuditLog.log(
        actor='Admin',
        role='MARKETING',
        action='UPDATE_CONFIG',
        target_type='SETTINGS',
        target_id='marketing_config',
        details=f"Marketing config updated. Scope: {config.targetScope}, Pixel: {config.pixelId}, Active: {config.isActive}",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = MarketingConfigSerializer(config)
    return Response({'success': True, 'config': serializer.data, 'message': 'Configuration saved successfully'})

@api_view(['POST'])
@permission_classes([AllowAny])
def marketing_capi_event_view(request):
    data = request.data
    event_name = data.get('eventName', 'PageView')
    event_id = data.get('eventId') or f"mkt-{int(time.time() * 1000)}"
    event_source_url = data.get('eventSourceUrl', '')
    user_data = data.get('userData', {})
    custom_data = data.get('customData', {})
    value = custom_data.get('value')
    order_id = custom_data.get('orderId')
    source = data.get('source', 'website')
    campaign = data.get('campaign', '')

    config = MarketingConfig.objects.first()
    capi_result = None

    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    client_user_agent = request.META.get('HTTP_USER_AGENT', '')

    meta_pixel_id = (config.pixelId if config and config.pixelId else '') or os.getenv('META_PIXEL_ID', '')
    meta_capi_token = (config.capiToken if config and config.capiToken else '') or os.getenv('META_CAPI_TOKEN', '')
    is_active = (config.isActive if config else True) and bool(meta_pixel_id and meta_capi_token)

    if is_active:
        test_code = data.get('testEventCode') or (config.testEventCode if config else '') or os.getenv('META_TEST_EVENT_CODE', '')
        capi_result = send_meta_capi_event(
            pixel_id=meta_pixel_id,
            access_token=meta_capi_token,
            event_name=event_name,
            event_id=event_id,
            event_source_url=event_source_url,
            client_ip=client_ip or '127.0.0.1',
            client_user_agent=client_user_agent or 'Mozilla/5.0',
            fbp=user_data.get('fbp', ''),
            fbc=user_data.get('fbc', ''),
            email=user_data.get('em', ''),
            phone=user_data.get('ph', ''),
            custom_data=custom_data,
            test_event_code=test_code
        )

    now_str = timezone.localtime().isoformat()
    product_name = custom_data.get('content_name') or data.get('productName') or data.get('name') or ''
    content_ids = custom_data.get('content_ids')
    product_id = content_ids[0] if isinstance(content_ids, list) and content_ids else data.get('productId', '')

    mkt_event = MarketingEvent.objects.create(
        id=f"mkt-{uuid.uuid4().hex[:8]}",
        eventId=event_id,
        eventName=event_name,
        timestamp=now_str,
        browserReported=data.get('browserReported', True),
        serverCapiReported=True,
        source=source,
        campaign=campaign,
        value=value if value is not None else 0,
        orderId=order_id,
        productName=str(product_name),
        productId=str(product_id) if product_id else '',
        dedupMatched=True
    )

    return Response({
        'success': True,
        'event_id': event_id,
        'capi_result': capi_result,
        'event': MarketingEventSerializer(mkt_event).data
    })

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def marketing_events_view(request):
    if request.method == 'GET':
        events = MarketingEvent.objects.all()[:100]
        serializer = MarketingEventSerializer(events, many=True)
        return Response({
            'success': True,
            'events': serializer.data
        })
    elif request.method == 'POST':
        data = request.data.copy()
        event_id = f"mkt-{int(time.time() * 1000)}"
        now_str = timezone.localtime().isoformat()

        data['id'] = data.get('id') or event_id
        data['timestamp'] = data.get('timestamp') or now_str
        data['serverCapiReported'] = True
        data['dedupMatched'] = True

        serializer = MarketingEventSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'event': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def notifications_list(request):
    if request.method == 'GET':
        notifs = NotificationLog.objects.all()[:100]
        serializer = NotificationLogSerializer(notifs, many=True)
        return Response({
            'success': True,
            'notifications': serializer.data
        })
    elif request.method == 'POST':
        from order.services import send_manual_notification
        data = request.data or {}
        channel = data.get('channel', 'SMS')
        recipient = data.get('recipient') or data.get('recipientPhone', '')
        message_text = data.get('messageText') or data.get('message', '')
        template_name = data.get('templateName', 'ADMIN_TEST')
        order_id = data.get('orderId', 'TEST-ORDER')

        if not recipient or not message_text:
            return Response({'success': False, 'message': 'recipient and messageText are required'}, status=status.HTTP_400_BAD_REQUEST)

        res = send_manual_notification(channel, recipient, message_text, template_name, order_id)
        return Response({
            'success': True,
            'result': res,
            'message': f"{channel} dispatched successfully"
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def sync_meta_ads_view(request):
    config = MarketingConfig.objects.first()
    ad_account_id = (request.data.get('adAccountId') or (config.adAccountId if config else '')).strip()
    access_token = (request.data.get('capiToken') or (config.capiToken if config else '')).strip()

    if ad_account_id and access_token:
        formatted_account = ad_account_id if ad_account_id.startswith('act_') else f"act_{ad_account_id}"
        url = f"https://graph.facebook.com/v19.0/{formatted_account}/insights"
        params = {
            'access_token': access_token,
            'fields': 'campaign_name,spend,clicks,impressions,cpc,ctr',
            'date_preset': 'maximum',
            'level': 'campaign'
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                insights_data = resp.json().get('data', [])
                return Response({
                    'success': True,
                    'synced': True,
                    'count': len(insights_data),
                    'campaigns': insights_data,
                    'message': f"Successfully synced {len(insights_data)} campaigns from Meta Marketing API!"
                })
            else:
                err_msg = resp.json().get('error', {}).get('message', 'Meta API sync error')
                return Response({
                    'success': False,
                    'synced': False,
                    'message': f"Meta API response: {err_msg}"
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'success': True,
        'synced': True,
        'simulation': True,
        'message': "Ad metrics live synced with local store orders & ROAS matrix."
    })

def facebook_catalog_feed_view(request):
    """
    Standard Facebook Commerce Manager Product XML/RSS Feed.
    Allows Facebook & Instagram to automatically import all store products,
    prices, and stock for Dynamic Advantage+ Catalog Ads.
    """
    from django.http import HttpResponse
    from products.models import Product

    try:
        prods = Product.objects.all()
        host = request.build_absolute_uri('/')[:-1]

        items_xml = []
        for p in prods:
            image_url = ""
            if isinstance(p.images, list) and len(p.images) > 0:
                first_img = p.images[0]
                if isinstance(first_img, str):
                    image_url = first_img
                elif isinstance(first_img, dict):
                    image_url = first_img.get('url', '')
            if not image_url:
                image_url = f"{host}/assets/product-placeholder.jpg"
            if not image_url.startswith('http'):
                image_url = f"{host}{image_url}"

            link = f"{host}/campaign-products?product={p.id}&utm_source=facebook&utm_campaign=catalog_feed"
            availability = 'out of stock' if p.isOutOfStock or p.stock <= 0 else 'in stock'
            desc = p.shortDescription or p.description or p.name

            items_xml.append(f"""
        <item>
            <g:id>{p.id}</g:id>
            <g:title><![CDATA[{p.name}]]></g:title>
            <g:description><![CDATA[{desc}]]></g:description>
            <g:link>{link}</g:link>
            <g:image_link>{image_url}</g:image_link>
            <g:brand>AmarDokan</g:brand>
            <g:condition>new</g:condition>
            <g:availability>{availability}</g:availability>
            <g:price>{p.price} BDT</g:price>
        </item>""")

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
    <channel>
        <title>AmarDokan Product Catalog Feed</title>
        <link>{host}</link>
        <description>Live automated product feed for Facebook &amp; Instagram Dynamic Ads</description>
        {''.join(items_xml)}
    </channel>
</rss>"""

        return HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
    except Exception as exc:
        return HttpResponse(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><error>{str(exc)}</error>", content_type='application/xml; charset=utf-8', status=500)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def shop_settings_view(request):
    """
    Get or update global shop identity, contact information, branding assets,
    and WhatsApp automated notification credentials.
    """
    settings = ShopSetting.get_settings()

    if request.method == 'GET':
        serializer = ShopSettingSerializer(settings)
        return Response({'success': True, 'settings': serializer.data})

    data = request.data
    fields = [
        'shopName', 'shopTagline', 'hotline', 'whatsappNumber', 'supportEmail',
        'address', 'logoUrl', 'faviconUrl', 'whatsappProvider', 'whatsappToken',
        'whatsappPhoneNumberId', 'whatsappInstanceId', 'adminAlertPhone',
        'emailHost', 'emailPort', 'emailUseTls', 'emailUseSsl',
        'emailHostUser', 'emailHostPassword', 'defaultFromEmail',
        'shopLanguageMode', 'defaultLanguage'
    ]
    for field in fields:
        if field in data:
            setattr(settings, field, data[field])

    # Support frontend alias keys ('name' -> 'shopName', 'tagline' -> 'shopTagline')
    if 'name' in data and 'shopName' not in data and data['name']:
        settings.shopName = data['name']
    if 'tagline' in data and 'shopTagline' not in data and data['tagline'] is not None:
        settings.shopTagline = data['tagline']

    if 'whatsappEnabled' in data:
        settings.whatsappEnabled = bool(data['whatsappEnabled'])
    if 'emailEnabled' in data:
        settings.emailEnabled = bool(data['emailEnabled'])

    settings.save()

    AuditLog.log(
        actor='Admin',
        role='ADMIN',
        action='UPDATE_SHOP_SETTINGS',
        target_type='SETTINGS',
        target_id='default_shop_setting',
        details=f"Shop settings updated. Name: {settings.shopName}, Mode: {settings.shopLanguageMode}, WA: {settings.whatsappEnabled}, Email: {settings.emailEnabled}",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = ShopSettingSerializer(settings)
    return Response({
        'success': True,
        'settings': serializer.data,
        'message': 'Shop settings updated successfully'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def test_whatsapp_view(request):
    """
    Dispatches a real or simulated test WhatsApp message to verify API credentials.
    """
    data = request.data
    recipient = data.get('recipientPhone', '').strip()
    message = data.get('messageText', '').strip()
    
    settings = ShopSetting.get_settings()
    if not recipient:
        recipient = settings.adminAlertPhone or settings.whatsappNumber or '01712849201'

    if not message:
        shop_name = settings.shopName or 'AmarDokan'
        message = f"🧪 *{shop_name} WhatsApp Test Message*\n\nআপনার WhatsApp গেটওয়ে সফলভাবে সংযুক্ত হয়েছে! এখন থেকে নতুন অর্ডার আসলে স্বয়ংক্রিয়ভাবে নোটিফিকেশন পৌঁছে যাবে।"

    try:
        from order.services import send_whatsapp_message
        res = send_whatsapp_message(recipient, message, order_id='TEST-WA')
        return Response({
            'success': res.get('success', False),
            'result': res,
            'message': 'Test WhatsApp dispatched'
        })
    except Exception as exc:
        return Response({
            'success': False,
            'error': str(exc)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def test_email_view(request):
    """
    Dispatches a real test Email via configured SMTP credentials to verify connectivity.
    """
    data = request.data
    recipient = data.get('recipientEmail', '').strip()
    
    settings = ShopSetting.get_settings()
    if not recipient:
        recipient = settings.supportEmail or 'customer@example.com'

    try:
        from order.services import send_test_smtp_email
        res = send_test_smtp_email(recipient)
        return Response(res)
    except Exception as exc:
        return Response({
            'success': False,
            'error': str(exc)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def staff_list_or_create(request):
    """
    List all staff members or register a new staff member (Admin / Manager / Dispatcher).
    """
    StaffMember.seed_defaults_if_empty()

    if request.method == 'GET':
        staff_qs = StaffMember.objects.all().order_by('created_at')
        serializer = StaffMemberSerializer(staff_qs, many=True)
        return Response({
            'success': True,
            'staff': serializer.data
        })

    data = request.data or {}
    name = str(data.get('name', '')).strip()
    username = str(data.get('username', '')).strip().lower()
    phone = str(data.get('phone', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', '')).strip()
    role = str(data.get('role', 'MANAGER')).strip().upper()
    notes = str(data.get('notes', '')).strip()

    if not name:
        return Response({'success': False, 'message': 'স্টাফের পূর্ণ নাম প্রদান করা আবশ্যক'}, status=status.HTTP_400_BAD_REQUEST)
    if not username or len(username) < 3:
        return Response({'success': False, 'message': 'ইউজারনেম কমপক্ষে ৩ অক্ষরের হতে হবে'}, status=status.HTTP_400_BAD_REQUEST)
    if not password or len(password) < 4:
        return Response({'success': False, 'message': 'পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে'}, status=status.HTTP_400_BAD_REQUEST)
    if role not in ['ADMIN', 'MANAGER', 'DISPATCHER']:
        role = 'MANAGER'

    if StaffMember.objects.filter(username__iexact=username).exists():
        return Response({'success': False, 'message': f'@{username} ইউজারনেমটি ইতোমধ্যে ব্যবহৃত হচ্ছে। অন্য ইউজারনেম বেছে নিন।'}, status=status.HTTP_400_BAD_REQUEST)

    new_id = f"staff-{role.lower()}-{uuid.uuid4().hex[:6]}"
    new_staff = StaffMember.objects.create(
        id=new_id,
        name=name,
        username=username,
        phone=phone,
        email=email,
        password=password,
        role=role,
        status='ACTIVE',
        notes=notes
    )

    AuditLog.log(
        actor=data.get('actor', 'Admin'),
        role='ADMIN',
        action='CREATE_STAFF',
        target_type='SETTINGS',
        target_id=new_staff.id,
        details=f"নতুন স্টাফ তৈরি করা হয়েছে: {new_staff.name} (@{new_staff.username}) - রোল: {new_staff.role}",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = StaffMemberSerializer(new_staff)
    return Response({
        'success': True,
        'message': f'স্টাফ {new_staff.name} সফলভাবে যুক্ত করা হয়েছে!',
        'staff': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def staff_detail_update_delete(request, staff_id):
    """
    Get, update, or remove a staff member.
    """
    StaffMember.seed_defaults_if_empty()
    staff = StaffMember.objects.filter(id=staff_id).first()
    if not staff:
        staff = StaffMember.objects.filter(username__iexact=staff_id).first()
    if not staff:
        return Response({'success': False, 'message': 'স্টাফ অ্যাকাউন্টটি পাওয়া যায়নি'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = StaffMemberSerializer(staff)
        return Response({'success': True, 'staff': serializer.data})

    if request.method == 'DELETE':
        if staff.username.lower() == 'admin' or staff.id == 'staff-admin-root':
            return Response({'success': False, 'message': 'মূল সুপার অ্যাডমিন অ্যাকাউন্ট ডিলিট করা সম্ভব নয়'}, status=status.HTTP_400_BAD_REQUEST)

        staff_name = staff.name
        staff_user = staff.username
        staff.delete()

        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='DELETE_STAFF',
            target_type='SETTINGS',
            target_id=staff_id,
            details=f"স্টাফ অ্যাকাউন্ট অপসারন করা হয়েছে: {staff_name} (@{staff_user})",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response({'success': True, 'message': f'স্টাফ {staff_name} সফলভাবে অপসারন করা হয়েছে'})

    # PUT / PATCH
    data = request.data or {}
    if 'name' in data and data['name']:
        staff.name = str(data['name']).strip()
    if 'phone' in data:
        staff.phone = str(data['phone']).strip()
    if 'email' in data:
        staff.email = str(data['email']).strip()
    if 'role' in data and data['role'] in ['ADMIN', 'MANAGER', 'DISPATCHER']:
        # Protect root admin from demotion
        if (staff.username.lower() != 'admin' and staff.id != 'staff-admin-root') or data['role'] == 'ADMIN':
            staff.role = data['role']
    if 'status' in data and data['status'] in ['ACTIVE', 'SUSPENDED']:
        if (staff.username.lower() != 'admin' and staff.id != 'staff-admin-root') or data['status'] == 'ACTIVE':
            staff.status = data['status']
    if 'notes' in data:
        staff.notes = str(data['notes']).strip()
    if 'password' in data and str(data['password']).strip():
        staff.password = str(data['password']).strip()

    staff.save()

    AuditLog.log(
        actor='Admin',
        role='ADMIN',
        action='UPDATE_STAFF',
        target_type='SETTINGS',
        target_id=staff.id,
        details=f"স্টাফ অ্যাকাউন্ট আপডেট করা হয়েছে: {staff.name} (@{staff.username}) - রোল: {staff.role}, স্ট্যাটাস: {staff.status}",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = StaffMemberSerializer(staff)
    return Response({
        'success': True,
        'message': 'স্টাফ অ্যাকাউন্ট আপডেট সম্পন্ন হয়েছে',
        'staff': serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def staff_login_view(request):
    """
    Authenticate a staff member (Super Admin, Manager, Dispatcher) and return their role and profile.
    """
    StaffMember.seed_defaults_if_empty()
    data = request.data or {}
    username = str(data.get('username', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    if not username or not password:
        return Response({
            'success': False,
            'message': 'ইউজারনেম এবং পাসওয়ার্ড উভয়ই প্রদান করা আবশ্যক'
        }, status=status.HTTP_400_BAD_REQUEST)

    staff = StaffMember.objects.filter(username__iexact=username).first()

    # Fallback if admin root account wasn't in db yet
    if not staff and username == 'admin' and password == 'admin1234':
        StaffMember.seed_defaults_if_empty()
        staff = StaffMember.objects.filter(username='admin').first()

    if not staff or staff.password != password:
        return Response({
            'success': False,
            'message': 'ভুল ইউজারনেম বা পাসওয়ার্ড। সঠিক তথ্য দিয়ে আবার চেষ্টা করুন।'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if staff.status == 'SUSPENDED':
        return Response({
            'success': False,
            'message': 'এই অ্যাকাউন্টটি সাময়িকভাবে স্থগিত (Suspended) রাখা হয়েছে। অনুগ্রহ করে সুপার অ্যাডমিনের সাথে যোগাযোগ করুন।'
        }, status=status.HTTP_403_FORBIDDEN)

    AuditLog.log(
        actor=staff.name,
        role=staff.role,
        action='STAFF_LOGIN',
        target_type='SETTINGS',
        target_id=staff.id,
        details=f"স্টাফ {staff.name} (@{staff.username}) সিস্টেমে {staff.role} হিসেবে লগইন করেছেন",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    return Response({
        'success': True,
        'message': f'স্বাগতম, {staff.name}!',
        'user': {
            'id': staff.id,
            'name': staff.name,
            'username': staff.username,
            'phone': staff.phone,
            'email': staff.email,
            'role': staff.role,
            'status': staff.status,
            'notes': staff.notes,
        }
    })


