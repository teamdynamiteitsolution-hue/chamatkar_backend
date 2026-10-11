import os
import time
import json
import urllib.request
import urllib.parse
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from core.models import NotificationLog

def format_bangladesh_phone(phone: str) -> str:
    """
    Normalizes phone numbers to standard Bangladesh format: 8801XXXXXXXXX
    """
    if not phone:
        return ""
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if digits.startswith('880'):
        return digits
    if digits.startswith('01'):
        return f"88{digits}"
    if len(digits) == 10 and digits.startswith('1'):
        return f"880{digits}"
    return digits

def send_greenweb_sms(phone: str, message_text: str) -> dict:
    """
    Greenweb BD SMS Gateway HTTP Dispatcher.
    Uses Greenweb API (https://api.greenweb.com.bd/api.php).
    Falls back gracefully to simulation mode if no API token is configured.
    """
    token = os.environ.get('GREENWEB_SMS_TOKEN', '').strip()
    formatted_phone = format_bangladesh_phone(phone)

    if token and formatted_phone:
        try:
            url = "https://api.greenweb.com.bd/api.php"
            data = urllib.parse.urlencode({
                'token': token,
                'to': formatted_phone,
                'message': message_text,
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers={'User-Agent': 'AmarDokan-BD-ECommerce/1.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_text = response.read().decode('utf-8', errors='ignore')
                is_ok = 'Ok' in resp_text or response.status == 200
                return {
                    'success': is_ok,
                    'status': 'SENT' if is_ok else 'FAILED',
                    'provider': 'Greenweb_SMS',
                    'response': resp_text,
                    'live': True
                }
        except Exception as exc:
            return {
                'success': False,
                'status': 'FAILED',
                'provider': 'Greenweb_SMS',
                'error': str(exc),
                'live': True
            }

    # Simulation Mode for Development & Testing
    return {
        'success': True,
        'status': 'SENT',
        'provider': 'Greenweb_SMS',
        'simulated': True,
        'message': 'Simulated SMS dispatch via Greenweb Gateway'
    }

def send_whatsapp_message(phone: str, message_text: str, order_id: str = None) -> dict:
    """
    WhatsApp Automated Notification Dispatcher.
    Checks ShopSetting from database first for configured credentials (Meta WhatsApp Cloud API or UltraMsg API),
    then falls back to environment variables.
    Falls back gracefully to simulation mode if credentials are not configured.
    """
    meta_token = os.environ.get('WHATSAPP_TOKEN', '').strip()
    phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip()
    ultramsg_token = os.environ.get('ULTRAMSG_TOKEN', '').strip()
    ultramsg_instance = os.environ.get('ULTRAMSG_INSTANCE_ID', '').strip()
    provider_pref = 'META_CLOUD'

    try:
        from core.models import ShopSetting
        shop_set = ShopSetting.get_settings()
        if not shop_set.whatsappEnabled:
            return {
                'success': False,
                'status': 'DISABLED',
                'provider': 'WHATSAPP_DISABLED',
                'message': 'WhatsApp notifications are disabled in Shop Settings'
            }
        provider_pref = shop_set.whatsappProvider or 'META_CLOUD'
        if shop_set.whatsappToken:
            if provider_pref == 'ULTRAMSG':
                ultramsg_token = shop_set.whatsappToken.strip()
                if shop_set.whatsappInstanceId:
                    ultramsg_instance = shop_set.whatsappInstanceId.strip()
            else:
                meta_token = shop_set.whatsappToken.strip()
                if shop_set.whatsappPhoneNumberId:
                    phone_number_id = shop_set.whatsappPhoneNumberId.strip()
    except Exception as e:
        print("ShopSetting WhatsApp lookup notice:", e)

    formatted_phone = format_bangladesh_phone(phone)

    # 1. UltraMsg WhatsApp API (Priority if selected)
    if provider_pref == 'ULTRAMSG' and ultramsg_token and ultramsg_instance and formatted_phone:
        try:
            url = f"https://api.ultramsg.com/{ultramsg_instance}/messages/chat"
            data = urllib.parse.urlencode({
                'token': ultramsg_token,
                'to': formatted_phone,
                'body': message_text
            }).encode('utf-8')

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                return {
                    'success': True,
                    'status': 'SENT',
                    'provider': 'UltraMsg_WhatsApp',
                    'response': resp_data,
                    'live': True
                }
        except Exception as exc:
            return {
                'success': False,
                'status': 'FAILED',
                'provider': 'UltraMsg_WhatsApp',
                'error': str(exc),
                'live': True
            }

    # 2. Meta WhatsApp Cloud API
    if meta_token and phone_number_id and formatted_phone:
        try:
            url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "text",
                "text": {"body": message_text}
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Authorization': f'Bearer {meta_token}',
                    'Content-Type': 'application/json'
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                return {
                    'success': True,
                    'status': 'SENT',
                    'provider': 'Meta_WhatsApp_Cloud_API',
                    'response': resp_data,
                    'live': True
                }
        except Exception as exc:
            err_msg = str(exc)
            if hasattr(exc, 'read'):
                try:
                    err_body = exc.read().decode('utf-8')
                    err_json = json.loads(err_body)
                    meta_err = err_json.get('error', {}).get('message', err_body)
                    err_msg = f"{exc}: {meta_err}"
                except Exception:
                    pass
            return {
                'success': False,
                'status': 'FAILED',
                'provider': 'Meta_WhatsApp_Cloud_API',
                'error': err_msg,
                'live': True
            }

    # 3. UltraMsg fallback if credentials exist
    if ultramsg_token and ultramsg_instance and formatted_phone:
        try:
            url = f"https://api.ultramsg.com/{ultramsg_instance}/messages/chat"
            data = urllib.parse.urlencode({
                'token': ultramsg_token,
                'to': formatted_phone,
                'body': message_text
            }).encode('utf-8')

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                return {
                    'success': True,
                    'status': 'SENT',
                    'provider': 'UltraMsg_WhatsApp',
                    'response': resp_data,
                    'live': True
                }
        except Exception as exc:
            return {
                'success': False,
                'status': 'FAILED',
                'provider': 'UltraMsg_WhatsApp',
                'error': str(exc),
                'live': True
            }

    # Simulation Mode
    return {
        'success': True,
        'status': 'SENT',
        'provider': 'Meta_WhatsApp_Cloud_API (Simulated)',
        'simulated': True,
        'message': 'Simulated WhatsApp message dispatch - Configure API credentials in Admin Shop Details / Notifications to send live messages.'
    }


def get_courier_tracking_urls(courier_provider: str, tracking_id: str, order_id: str) -> dict:
    """
    Returns live tracking URLs for Bangladesh courier services.
    """
    prov_lower = (courier_provider or '').lower()
    carrier_url = ""

    if 'steadfast' in prov_lower:
        carrier_url = f"https://steadfast.com.bd/t/{tracking_id}"
    elif 'pathao' in prov_lower:
        carrier_url = f"https://merchant.pathao.com/tracking?consignment_id={tracking_id}"
    elif 'redx' in prov_lower:
        carrier_url = f"https://redx.com.bd/track?trackingId={tracking_id}"
    elif 'paperfly' in prov_lower:
        carrier_url = f"https://paperfly.com.bd/tracking?id={tracking_id}"
    elif 'ecourier' in prov_lower:
        carrier_url = f"https://ecourier.com.bd/tracking?ecr={tracking_id}"

    native_url = f"https://amardokan.com/track-order?id={order_id}"

    return {
        'carrier_url': carrier_url,
        'native_url': native_url
    }

def send_order_email(order, event: str) -> dict:
    """
    Automated Order Email Dispatcher with responsive HTML template and plain text fallback.
    Sends confirmation, invoice breakdown, and live tracking links with anti-spam protections.
    """
    address = order.address if isinstance(order.address, dict) else {}
    customer_name = address.get('customerName', 'সম্মানিত গ্রাহক')
    customer_email = (getattr(order, 'customerEmail', None) or address.get('email') or '').strip()
    
    if not customer_email or '@' not in customer_email:
        return {
            'success': False,
            'status': 'SKIPPED',
            'message': 'No valid customer email address provided'
        }

    now_str = time.strftime('%Y-%m-%d %H:%M:%S')

    # Shop Info
    shop_name = "AmarDokan"
    hotline = "09612345678"
    support_email = "support@amardokan.com"
    try:
        from core.models import ShopSetting
        s = ShopSetting.get_settings()
        if s.shopName:
            shop_name = s.shopName
        if s.hotline:
            hotline = s.hotline
        if getattr(s, 'supportEmail', None):
            support_email = s.supportEmail
    except Exception:
        pass

    # Courier Tracking
    courier_info = order.courier if isinstance(order.courier, dict) else {}
    prov_name = courier_info.get('provider', 'Courier').upper()
    trkid = courier_info.get('trackingId', 'N/A')

    frontend_url = os.environ.get('FRONTEND_URL') or os.environ.get('APP_URL') or getattr(settings, 'SSLCOMMERZ_FRONTEND_URL', 'http://localhost:3001')
    live_tracking_url = f"{frontend_url.rstrip('/')}/track-order?id={order.id}"

    # Event specific headers & text
    if event == 'ORDER_CREATED':
        subject = f"অর্ডার কনফার্মেশন: #{order.id} - {shop_name}"
        headline = "আপনার অর্ডার সফলভাবে গ্রহণ করা হয়েছে!"
        status_badge_text = "অর্ডার রিসিভড"
        status_badge_bg = "#10B981"
        sub_message = f"প্রিয় {customer_name}, {shop_name}-এ কেনাকাটা করার জন্য ধন্যবাদ! আপনার অর্ডার #{order.id} সফলভাবে গ্রহণ করা হয়েছে।"
    elif event == 'ORDER_CONFIRMED':
        subject = f"অর্ডার কনফার্ম হয়েছে: #{order.id} - {shop_name}"
        headline = "আপনার অর্ডার কনফার্ম করা হয়েছে!"
        status_badge_text = "কনফার্মড"
        status_badge_bg = "#3B82F6"
        sub_message = f"প্রিয় {customer_name}, আপনার অর্ডার #{order.id} কনফার্ম হয়েছে এবং পণ্য প্যাকিং চলছে।"
    elif event == 'SHIPMENT_CREATED':
        subject = f"পার্সেল কুরিয়ারে হস্তান্তর করা হয়েছে: #{order.id} - {shop_name}"
        headline = "আপনার পার্সেল কুরিয়ারে পাঠানো হয়েছে!"
        status_badge_text = f"ইন ট্রানজিট ({prov_name})"
        status_badge_bg = "#8B5CF6"
        sub_message = f"প্রিয় {customer_name}, আপনার পার্সেল {prov_name} কুরিয়ারে বুকিং সম্পন্ন হয়েছে। ট্র্যাকিং আইডি: {trkid}।"
    elif event == 'OUT_FOR_DELIVERY':
        subject = f"পার্সেল আজ ডেলিভারি হবে: #{order.id} - {shop_name}"
        headline = "পার্সেল আজ আপনার ঠিকানায় পৌঁছাবে!"
        status_badge_text = "আউট ফর ডেলিভারি"
        status_badge_bg = "#F59E0B"
        sub_message = f"প্রিয় {customer_name}, আমাদের ডেলিভারিম্যান পার্সেল নিয়ে রওনা হয়েছেন।"
    elif event == 'DELIVERED':
        subject = f"পার্সেল সফলভাবে ডেলিভারি সম্পন্ন: #{order.id} - {shop_name}"
        headline = "পার্সেল সফলভাবে ডেলিভারি সম্পন্ন হয়েছে!"
        status_badge_text = "ডেলিভার্ড"
        status_badge_bg = "#059669"
        sub_message = f"প্রিয় {customer_name}, আপনার অর্ডার #{order.id} ডেলিভারি সম্পন্ন হয়েছে। আমাদের সাথে থাকার জন্য ধন্যবাদ।"
    else:
        subject = f"অর্ডার আপডেট: #{order.id} - {shop_name}"
        headline = f"অর্ডার স্ট্যাটাস আপডেট: {event}"
        status_badge_text = event
        status_badge_bg = "#64748B"
        sub_message = f"প্রিয় {customer_name}, আপনার অর্ডার #{order.id}-এর স্ট্যাটাস আপডেট হয়েছে।"

    # Generate item rows
    items = order.items if isinstance(order.items, list) else []
    items_html = ""
    items_text_list = []

    for itm in items:
        name = itm.get('name', 'Product')
        qty = itm.get('quantity', 1)
        price = itm.get('price', 0)
        img = itm.get('image', '')
        variant = itm.get('variant') or itm.get('selectedColor') or itm.get('selectedSize') or ''
        variant_str = f" ({variant})" if variant else ""
        row_total = price * qty
        items_text_list.append(f"- {name}{variant_str} x{qty}: ৳{row_total}")

        img_td = ""
        if img:
            img_td = f'<td style="padding: 12px 8px; width: 50px; vertical-align: middle;"><img src="{img}" alt="{name}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0;" /></td>'

        items_html += f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            {img_td}
            <td style="padding: 12px 8px; vertical-align: middle;">
                <div style="font-weight: 600; color: #1e293b; font-size: 14px;">{name}</div>
                {f'<div style="font-size: 12px; color: #64748b;">ভেরিয়েন্ট: {variant}</div>' if variant else ''}
                <div style="font-size: 12px; color: #94a3b8;">৳{price} x {qty}</div>
            </td>
            <td style="padding: 12px 8px; text-align: right; vertical-align: middle; font-weight: 600; color: #0f172a; font-size: 14px;">
                ৳{row_total}
            </td>
        </tr>
        """

    items_text_plain = "\n".join(items_text_list)

    # Address block
    full_addr = address.get('fullAddress', '')
    thana = address.get('thana', '')
    district = address.get('district', '')
    phone = address.get('phone', '')
    addr_line = f"{full_addr}, {thana}, {district}".strip(', ')

    discount_row_html = ""
    discount_row_text = ""
    if order.discount and order.discount > 0:
        discount_row_html = f"""
        <tr>
            <td style="padding: 6px 0; color: #059669; font-size: 14px;">কুপন ডিসকাউন্ট:</td>
            <td style="padding: 6px 0; text-align: right; color: #059669; font-weight: 600; font-size: 14px;">-৳{order.discount}</td>
        </tr>
        """
        discount_row_text = f"কুপন ডিসকাউন্ট: -৳{order.discount}\n"

    # Plain Text representation (Anti-spam best practice)
    plain_text = f"""======================================================
{shop_name} - {subject}
======================================================
{sub_message}

অর্ডার নম্বর: #{order.id}
তারিখ: {now_str}
পেমেন্ট পদ্ধতি: {order.paymentMethod} ({order.paymentStatus})

ক্রয়কৃত পণ্যসমূহ:
{items_text_plain}

হিসাব বিবরণী:
সাবটোটাল: ৳{order.subtotal}
ডেলিভারি চার্জ: ৳{order.deliveryFee}
{discount_row_text}সর্বমোট প্রদেয়: ৳{order.total}

ডেলিভারি ঠিকানা:
নাম: {customer_name}
মোবাইল: {phone}
ঠিকানা: {addr_line}

লাইভ পার্সেল ট্র্যাকিং লিংক:
{live_tracking_url}

হেল্পলাইন ও কাস্টমার সাপোর্ট: {hotline} | {support_email}
======================================================
"""

    # Dynamic CTA button based on event (Review request for DELIVERED, Tracking for others)
    if event == 'DELIVERED':
        cta_button_html = f"""
    <!-- Delivered & Review CTA -->
    <div style="padding: 22px 24px; text-align: center; background-color: #ecfdf5; border-bottom: 1px solid #d1fae5;">
        <div style="font-size: 15px; font-weight: 700; color: #065f46; margin-bottom: 8px;">আপনার পার্সেল সফলভাবে ডেলিভারি সম্পন্ন হয়েছে 🎉</div>
        <p style="margin: 0 0 14px 0; font-size: 13px; color: #047857;">আমাদের পণ্য ও সেবার মান কেমন লেগেছে? আপনার মূল্যবান মতামত অন্যদের কেনাকাটায় সাহায্য করবে।</p>
        <a href="{live_tracking_url}#reviews" target="_blank" style="display: inline-block; background-color: #059669; color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; box-shadow: 0 4px 6px -1px rgba(5, 150, 105, 0.25);">
            ⭐ পণ্যের রিভিউ ও রেটিং দিন (Rate & Review)
        </a>
        <div style="font-size: 12px; color: #059669; margin-top: 10px;">অর্ডার আইডি: <strong>#{order.id}</strong></div>
    </div>
        """
    else:
        cta_button_html = f"""
    <!-- Live Tracking CTA -->
    <div style="padding: 20px 24px; text-align: center; background-color: #f0fdf4; border-bottom: 1px solid #dcfce7;">
        <a href="{live_tracking_url}" target="_blank" style="display: inline-block; background-color: #10b981; color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.25);">
            🚚 লাইভ পার্সেল ট্র্যাক করুন (Track Order)
        </a>
        <div style="font-size: 12px; color: #059669; margin-top: 8px;">অর্ডার আইডি: <strong>#{order.id}</strong></div>
    </div>
        """

    # Responsive HTML representation
    html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #334155; line-height: 1.5;">
<div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    
    <!-- Top Brand Bar -->
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px; text-align: center; color: #ffffff;">
        <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; color: #ffffff;">{shop_name}</h1>
        <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">স্মার্ট ও নির্ভরযোগ্য অনলাইন কেনাকাটা</p>
    </div>

    <!-- Status Banner -->
    <div style="padding: 24px 24px 16px 24px; text-align: center; border-bottom: 1px solid #f1f5f9;">
        <span style="display: inline-block; background-color: {status_badge_bg}; color: #ffffff; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 9999px; margin-bottom: 10px; text-transform: uppercase;">
            {status_badge_text}
        </span>
        <h2 style="margin: 0 0 8px 0; font-size: 20px; color: #0f172a; font-weight: 700;">{headline}</h2>
        <p style="margin: 0; font-size: 14px; color: #64748b;">{sub_message}</p>
    </div>

    {cta_button_html}

    <!-- Order Items -->
    <div style="padding: 20px 24px;">
        <h3 style="margin: 0 0 12px 0; font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; font-weight: 700;">অর্ডার আইটেমস ({len(items)})</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tbody>
                {items_html}
            </tbody>
        </table>
    </div>

    <!-- Invoice Summary -->
    <div style="padding: 16px 24px; background-color: #f8fafc; border-top: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 6px 0; color: #64748b; font-size: 14px;">সাবটোটাল:</td>
                <td style="padding: 6px 0; text-align: right; color: #1e293b; font-weight: 600; font-size: 14px;">৳{order.subtotal}</td>
            </tr>
            <tr>
                <td style="padding: 6px 0; color: #64748b; font-size: 14px;">ডেলিভারি চার্জ:</td>
                <td style="padding: 6px 0; text-align: right; color: #1e293b; font-weight: 600; font-size: 14px;">৳{order.deliveryFee}</td>
            </tr>
            {discount_row_html}
            <tr style="border-top: 1px dashed #cbd5e1;">
                <td style="padding: 12px 0 6px 0; color: #0f172a; font-weight: 700; font-size: 16px;">মোট প্রদেয় (Grand Total):</td>
                <td style="padding: 12px 0 6px 0; text-align: right; color: #10b981; font-weight: 800; font-size: 18px;">৳{order.total}</td>
            </tr>
            <tr>
                <td style="padding: 2px 0; color: #64748b; font-size: 12px;">পেমেন্ট পদ্ধতি:</td>
                <td style="padding: 2px 0; text-align: right; color: #475569; font-weight: 600; font-size: 12px;">{order.paymentMethod} ({order.paymentStatus})</td>
            </tr>
        </table>
    </div>

    <!-- Delivery Address Details -->
    <div style="padding: 20px 24px; border-bottom: 1px solid #f1f5f9;">
        <h3 style="margin: 0 0 10px 0; font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; font-weight: 700;">ডেলিভারি ঠিকানা</h3>
        <div style="font-size: 14px; color: #1e293b; line-height: 1.6;">
            <strong>{customer_name}</strong><br>
            📞 {phone}<br>
            📍 {addr_line}
        </div>
    </div>

    <!-- Footer & Anti-Spam Safeguards -->
    <div style="padding: 24px; text-align: center; background-color: #ffffff; color: #94a3b8; font-size: 12px; line-height: 1.6;">
        <p style="margin: 0 0 6px 0;">যেকোনো সহায়তায় আমাদের কল করুন: <strong style="color: #475569;">{hotline}</strong> অথবা ইমেইল করুন: <a href="mailto:{support_email}" style="color: #10b981; text-decoration: none;">{support_email}</a></p>
        <p style="margin: 0 0 12px 0;">আপনি {shop_name}-এ অর্ডার সম্পন্ন করায় এই নিশ্চিতকরণ ইমেইলটি পাঠানো হয়েছে।</p>
        <div style="border-top: 1px solid #f1f5f9; padding-top: 12px; color: #cbd5e1;">
            © 2026 {shop_name}. All rights reserved.
        </div>
    </div>

</div>
</body>
</html>
"""

    # Check if ShopSetting has custom SMTP credentials configured
    conn = None
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f'{shop_name} <orders@amardokan.com>')
    provider_name = 'Django_SMTP_Email'
    try:
        from core.models import ShopSetting
        s = ShopSetting.get_settings()
        if not s.emailEnabled:
            return {
                'success': False,
                'status': 'DISABLED',
                'message': 'Automated email dispatch is disabled in Admin settings'
            }
        if s.defaultFromEmail:
            from_email = s.defaultFromEmail
        if s.emailHostUser and s.emailHostPassword:
            provider_name = f"SMTP ({s.emailHost})"
            from django.core.mail import get_connection
            conn = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=s.emailHost or 'smtp.gmail.com',
                port=int(s.emailPort or 587),
                username=s.emailHostUser.strip(),
                password=s.emailHostPassword.strip(),
                use_tls=bool(s.emailUseTls),
                use_ssl=bool(s.emailUseSsl),
                timeout=12,
            )
    except Exception as exc:
        print("[SMTP Config Lookup Notice]", exc)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=from_email,
            to=[customer_email],
            connection=conn
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        # Log to NotificationLog
        email_log = NotificationLog.objects.create(
            id=f"notif-email-{int(time.time() * 1000)}",
            orderId=order.id,
            channel='EMAIL',
            recipient=customer_email,
            templateName=f"{event}_EMAIL",
            messageText=f"{subject}\n{plain_text[:200]}...",
            status='SENT',
            timestamp=now_str,
            provider=provider_name
        )

        return {
            'success': True,
            'status': 'SENT',
            'provider': provider_name,
            'logId': email_log.id,
            'log': email_log
        }
    except Exception as exc:
        print(f"[Email Notification Error] Failed to send email for #{order.id}: {exc}")
        try:
            fail_log = NotificationLog.objects.create(
                id=f"notif-email-{int(time.time() * 1000)}",
                orderId=order.id,
                channel='EMAIL',
                recipient=customer_email,
                templateName=f"{event}_EMAIL",
                messageText=f"{subject} [FAILED: {exc}]",
                status='FAILED',
                timestamp=now_str,
                provider='Django_SMTP_Email'
            )
            return {
                'success': False,
                'status': 'FAILED',
                'error': str(exc),
                'logId': fail_log.id,
                'log': fail_log
            }
        except Exception:
            return {
                'success': False,
                'status': 'FAILED',
                'error': str(exc)
            }


def dispatch_order_notifications(order, event: str):
    """
    Dispatches automated Email, SMS and WhatsApp messages for order lifecycle events:
    - ORDER_CREATED
    - ORDER_CONFIRMED
    - SHIPMENT_CREATED (includes courier tracking link)
    - OUT_FOR_DELIVERY
    - DELIVERED
    """
    address = order.address if isinstance(order.address, dict) else {}
    customer_name = address.get('customerName', 'গ্রাহক')
    phone = address.get('phone', '')
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')

    logs = []

    # 0. Dispatch Automated Order Email
    email_res = send_order_email(order, event)
    if email_res.get('log'):
        logs.append(email_res['log'])

    if not phone:
        return logs

    # Extract Courier Info
    courier_info = order.courier if isinstance(order.courier, dict) else {}
    prov_name = courier_info.get('provider', 'Courier').upper()
    trkid = courier_info.get('trackingId', 'N/A')
    tracking_urls = get_courier_tracking_urls(prov_name, trkid, order.id)

    # Dynamic Shop settings
    shop_name = "AmarDokan"
    hotline = "09612345678"
    admin_alert_phone = ""
    try:
        from core.models import ShopSetting
        s = ShopSetting.get_settings()
        if s.shopName:
            shop_name = s.shopName
        if s.hotline:
            hotline = s.hotline
        if s.adminAlertPhone:
            admin_alert_phone = s.adminAlertPhone
    except Exception:
        pass

    # 1. Build SMS Text
    sms_text = ""
    if event == 'ORDER_CREATED':
        sms_text = f"{shop_name}: প্রিয় {customer_name}, আপনার অর্ডার #{order.id} (৳{order.total}) সফলভাবে গৃহীত হয়েছে! শীঘ্রই কনফার্মেশনের জন্য কল করা হবে। হেল্পলাইন: {hotline}"
    elif event == 'ORDER_CONFIRMED':
        sms_text = f"{shop_name}: আপনার অর্ডার #{order.id} কনফার্ম করা হয়েছে। পণ্যটি গোডাউন থেকে প্যাকিং করা হচ্ছে। ধন্যবাদ সাথে থাকার জন্য!"
    elif event == 'SHIPMENT_CREATED':
        track_link = tracking_urls['carrier_url'] or tracking_urls['native_url']
        sms_text = f"{shop_name}: আপনার অর্ডার #{order.id} কুরিয়ারে হস্তান্তর করা হয়েছে ({prov_name} ট্র্যাকিং: {trkid})। লাইভ ট্র্যাক করুন: {track_link}"
    elif event == 'OUT_FOR_DELIVERY':
        collection_amount = order.total if order.paymentMethod == 'COD' else 0
        sms_text = f"{shop_name}: প্রিয় গ্রাহক, আপনার পার্সেলটি আজ ডেলিভারিম্যানের কাছে রয়েছে। ডেলিভারি গ্রহণের সময় প্রস্তুত থাকুন (কালেকশন: ৳{collection_amount})।"
    elif event == 'DELIVERED':
        sms_text = f"{shop_name}: আপনার অর্ডার #{order.id} সফলভাবে ডেলিভারি সম্পন্ন হয়েছে। পণ্যে কোনো সমস্যা থাকলে ৭ দিনের মধ্যে আমাদের জানান।"

    if sms_text:
        sms_res = send_greenweb_sms(phone, sms_text)
        sms_log = NotificationLog.objects.create(
            id=f"notif-sms-{int(time.time() * 1000)}",
            orderId=order.id,
            channel='SMS',
            recipient=phone,
            templateName=event,
            messageText=sms_text,
            status=sms_res.get('status', 'SENT'),
            timestamp=now_str,
            provider='Greenweb_SMS'
        )
        logs.append(sms_log)

    # 2. Build WhatsApp Text
    wa_text = ""
    items_list = ", ".join([f"{item.get('name', 'Product')} (x{item.get('quantity', 1)})" for item in order.items]) if isinstance(order.items, list) else ""
    if event == 'ORDER_CREATED':
        wa_text = (
            f"🛍️ *অর্ডার রিসিভ হয়েছে - {shop_name}*\n\n"
            f"প্রিয় *{customer_name}*,\n"
            f"আপনার অর্ডার *#{order.id}* সফলভাবে সিস্টেমে যুক্ত হয়েছে।\n\n"
            f"📦 *আইটেম:* {items_list}\n"
            f"💰 *মোট প্রদেয়:* ৳{order.total} ({order.paymentMethod})\n"
            f"📍 *ঠিকানা:* {address.get('fullAddress', '')}, {address.get('district', '')}\n\n"
            f"অর্ডার ট্র্যাক করতে ভিজিট করুন: https://amardokan.com/track-order?id={order.id}\n"
            f"হেল্পলাইন: {hotline}\n"
            f"ধন্যবাদ!"
        )
    elif event == 'ORDER_CONFIRMED':
        wa_text = (
            f"✅ *অর্ডার কনফার্ম হয়েছে - {shop_name}*\n\n"
            f"প্রিয় *{customer_name}*,\n"
            f"আপনার অর্ডার *#{order.id}* সফলভাবে কনফার্ম করা হয়েছে এবং প্যাকিং চলছে।\n\n"
            f"📲 লাইভ স্ট্যাটাস চেক করুন:\nhttps://amardokan.com/track-order?id={order.id}\n\n"
            f"ধন্যবাদ!"
        )
    elif event == 'SHIPMENT_CREATED':
        track_link = tracking_urls['carrier_url'] or tracking_urls['native_url']
        wa_text = (
            f"🚚 *পার্সেল কুরিয়ারে বুকিং সম্পন্ন - {shop_name}*\n\n"
            f"প্রিয় *{customer_name}*,\n"
            f"আপনার অর্ডার *#{order.id}* কুরিয়ারে হস্তান্তর করা হয়েছে।\n\n"
            f"📦 *কুরিয়ার:* {prov_name}\n"
            f"🔖 *ট্র্যাকিং কোড:* {trkid}\n\n"
            f"📲 *লাইভ কুরিয়ার ট্র্যাকিং লিংক:*\n{track_link}\n\n"
            f"ধন্যবাদ আমাদের সাথে থাকার জন্য!"
        )
    elif event == 'OUT_FOR_DELIVERY':
        collection_amount = order.total if order.paymentMethod == 'COD' else 0
        wa_text = (
            f"🚴 *পার্সেল আজ ডেলিভারি হবে - {shop_name}*\n\n"
            f"প্রিয় *{customer_name}*,\n"
            f"আপনার অর্ডার *#{order.id}* ডেলিভারি রাইডারের কাছে রয়েছে। আজই আপনার ঠিকানায় পৌঁছে যাবে।\n\n"
            f"💵 *কালেকশন মূল্য:* ৳{collection_amount}\n"
            f"📲 লাইভ ট্র্যাক করুন:\nhttps://amardokan.com/track-order?id={order.id}\n\n"
            f"অনুগ্রহ করে ফোন সচল রাখুন।"
        )
    elif event == 'DELIVERED':
        wa_text = (
            f"🎉 *পার্সেল সফলভাবে ডেলিভারি সম্পন্ন! - {shop_name}*\n\n"
            f"প্রিয় *{customer_name}*,\n"
            f"আপনার অর্ডার *#{order.id}* ডেলিভারি সম্পন্ন হয়েছে। আশা করি আপনার পছন্দের পণ্যটি ভালো লেগেছে!\n\n"
            f"যেকোনো প্রয়োজনে আমাদের সাথে যোগাযোগ করুন। ধন্যবাদ {shop_name}-এ কেনাকাটা করার জন্য!"
        )

    if wa_text:
        wa_res = send_whatsapp_message(phone, wa_text, order_id=order.id)
        wa_log = NotificationLog.objects.create(
            id=f"notif-wa-{int(time.time() * 1000)}",
            orderId=order.id,
            channel='WHATSAPP',
            recipient=phone,
            templateName=event + '_WA',
            messageText=wa_text,
            status=wa_res.get('status', 'SENT'),
            timestamp=now_str,
            provider=wa_res.get('provider', 'Meta_WhatsApp_Cloud_API')
        )
        logs.append(wa_log)

    # 3. Admin WhatsApp Notification on new order
    if admin_alert_phone and event == 'ORDER_CREATED':
        try:
            admin_wa_text = (
                f"🚨 *নতুন অর্ডার অ্যালার্ট! - {shop_name}*\n\n"
                f"অর্ডার নম্বর: *#{order.id}*\n"
                f"👤 গ্রাহক: *{customer_name}* ({phone})\n"
                f"💰 বিল: ৳{order.total} ({order.paymentMethod})\n"
                f"📦 আইটেম: {items_list}\n"
                f"📍 ঠিকানা: {address.get('fullAddress', '')}, {address.get('district', '')}\n\n"
                f"অ্যাডমিন প্যানেল থেকে অর্ডারটি ভেরিফাই ও বুকিং সম্পন্ন করুন।"
            )
            admin_wa_res = send_whatsapp_message(admin_alert_phone, admin_wa_text, order_id=f"admin-{order.id}")
            NotificationLog.objects.create(
                id=f"notif-wa-admin-{int(time.time() * 1000)}",
                orderId=order.id,
                channel='WHATSAPP',
                recipient=admin_alert_phone,
                templateName='ADMIN_ALERT_WA',
                messageText=admin_wa_text,
                status=admin_wa_res.get('status', 'SENT'),
                timestamp=now_str,
                provider=admin_wa_res.get('provider', 'Meta_WhatsApp_Cloud_API')
            )
        except Exception as e:
            print("Admin WhatsApp alert error:", e)

    return logs

def send_manual_notification(channel: str, recipient: str, message_text: str, template_name: str = 'MANUAL', order_id: str = 'ADMIN-DISPATCH') -> dict:
    """
    Sends a test or manual notification from Admin console and logs to database.
    """
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    channel_upper = (channel or 'SMS').upper()

    if channel_upper == 'SMS':
        res = send_greenweb_sms(recipient, message_text)
        prov = res.get('provider', 'Greenweb_SMS')
    elif channel_upper == 'EMAIL':
        conn = None
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Chomotkar BD <orders@amardokan.com>')
        prov = 'Django_SMTP_Email'
        try:
            from core.models import ShopSetting
            s = ShopSetting.get_settings()
            if s.defaultFromEmail:
                from_email = s.defaultFromEmail
            if s.emailHostUser and s.emailHostPassword:
                prov = f"SMTP ({s.emailHost})"
                from django.core.mail import get_connection
                conn = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=s.emailHost or 'smtp.gmail.com',
                    port=int(s.emailPort or 587),
                    username=s.emailHostUser.strip(),
                    password=s.emailHostPassword.strip(),
                    use_tls=bool(s.emailUseTls),
                    use_ssl=bool(s.emailUseSsl),
                    timeout=12,
                )
        except Exception:
            pass

        subject = f"Notification from AmarDokan - #{order_id}"
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message_text,
                from_email=from_email,
                to=[recipient],
                connection=conn
            )
            html_body = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #0f172a; margin-top: 0;">AmarDokan Notice</h2>
                <div style="font-size: 15px; color: #334155; line-height: 1.6; white-space: pre-wrap;">{message_text}</div>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 0;">AmarDokan E-Commerce Platform</p>
            </div>"""
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
            res = {'success': True, 'status': 'SENT', 'provider': prov}
        except Exception as e:
            res = {'success': False, 'status': 'FAILED', 'error': str(e), 'provider': prov}
    else:
        res = send_whatsapp_message(recipient, message_text, order_id=order_id)
        prov = res.get('provider', 'Meta_WhatsApp_Cloud_API')


    log_entry = NotificationLog.objects.create(
        id=f"notif-{channel_upper.lower()}-{int(time.time() * 1000)}",
        orderId=order_id,
        channel=channel_upper,
        recipient=recipient,
        templateName=template_name,
        messageText=message_text,
        status=res.get('status', 'SENT'),
        timestamp=now_str,
        provider=prov
    )

    return {
        'success': res.get('success', True),
        'status': res.get('status', 'SENT'),
        'provider': prov,
        'logId': log_entry.id,
        'timestamp': now_str
    }


def send_test_smtp_email(recipient_email: str):
    """
    Sends a test verification email using ShopSetting SMTP credentials.
    """
    from core.models import ShopSetting
    s = ShopSetting.get_settings()
    shop_name = s.shopName or "AmarDokan BD"
    subject = f"🧪 {shop_name} SMTP Email Gateway Connection Test"
    body = (
        f"Hello,\n\n"
        f"This is an automated test email from {shop_name}.\n"
        f"Your SMTP email server configuration has been successfully connected!\n\n"
        f"Order confirmations, tracking updates, and delivery alerts will now be dispatched automatically to your customers."
    )
    html_content = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 520px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; color: #1e293b;">
        <div style="background: #10b981; color: white; padding: 12px 20px; border-radius: 8px; font-weight: bold; font-size: 16px; margin-bottom: 16px;">
            ✓ SMTP Email Gateway Connected Successfully
        </div>
        <h3 style="margin: 0 0 8px 0; color: #0f172a;">{shop_name}</h3>
        <p style="font-size: 14px; color: #475569; line-height: 1.6;">
            অভিনন্দন! আপনার SMTP ইমেইল সার্ভার সফলভাবে সংযুক্ত হয়েছে। এখন থেকে স্টোরে নতুন অর্ডার আসলে, কুরিয়ারে পার্সেল বুকিং হলে এবং ডেলিভারি সম্পন্ন হলে স্বয়ংক্রিয়ভাবে গ্রাহকদের কাছে ট্র্যাকিং লিংকসহ ইমেইল পৌঁছে যাবে।
        </p>
        <div style="background: #f8fafc; border: 1px solid #f1f5f9; padding: 12px; border-radius: 8px; font-size: 12px; color: #64748b; margin-top: 16px;">
            Host: {s.emailHost or 'smtp.gmail.com'} | Port: {s.emailPort} | TLS: {str(s.emailUseTls)} | User: {s.emailHostUser or 'Not specified'}
        </div>
    </div>"""

    conn = None
    from_email = s.defaultFromEmail or getattr(settings, 'DEFAULT_FROM_EMAIL', f'{shop_name} <orders@amardokan.com>')
    provider_name = 'Django_Console_Email'

    if s.emailHostUser and s.emailHostPassword:
        provider_name = f"SMTP ({s.emailHost})"
        from django.core.mail import get_connection
        conn = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=s.emailHost or 'smtp.gmail.com',
            port=int(s.emailPort or 587),
            username=s.emailHostUser.strip(),
            password=s.emailHostPassword.strip(),
            use_tls=bool(s.emailUseTls),
            use_ssl=bool(s.emailUseSsl),
            timeout=12,
        )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[recipient_email],
        connection=conn
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)

    return {
        'success': True,
        'message': f'Test email sent to {recipient_email} successfully via {provider_name}!',
        'provider': provider_name,
    }
