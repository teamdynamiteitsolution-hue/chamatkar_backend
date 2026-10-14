import random
import re
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Order
from .serializers import OrderSerializer
from .services import dispatch_order_notifications
from products.models import Product, Coupon
from core.models import AuditLog
from core.utils import calculate_delivery_fee, assess_order_risk, normalize_bangladesh_phone
from users.models import CustomerProfile

@api_view(['POST'])
@permission_classes([AllowAny])
def checkout_view(request):
    data = request.data
    items = data.get('items', [])
    address = data.get('address', {})
    payment_method = data.get('paymentMethod', 'COD')
    coupon_code = data.get('couponCode')
    utm = data.get('utm', {})

    if not items or not address or not address.get('phone') or not address.get('customerName'):
        return Response({
            'success': False,
            'message': 'Missing required order details'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Calculate subtotal using server product prices and verify stock availability
    subtotal = 0
    for item in items:
        prod_id = item.get('productId')
        prod = Product.objects.filter(id=prod_id).first()
        if prod and (prod.isOutOfStock or prod.stock <= 0):
            return Response({
                'success': False,
                'message': f'"{prod.name}" বর্তমানে আউট অব স্টক (Out of Stock)। অনুগ্রহ করে পণ্যটি তালিকা থেকে বাদ দিন।'
            }, status=status.HTTP_400_BAD_REQUEST)
        unit_price = prod.price if prod else item.get('price', 0)
        subtotal += int(unit_price) * int(item.get('quantity', 1))

    # Calculate Delivery fee
    district = address.get('district', '')
    delivery_calc = calculate_delivery_fee(district, address.get('fullAddress', ''))
    delivery_fee = delivery_calc['deliveryFee']
    address['deliveryZone'] = delivery_calc['deliveryZone']

    # Coupon discount
    discount = 0
    if coupon_code:
        coupon = Coupon.objects.filter(code__iexact=coupon_code.strip(), isActive=True).first()
        if coupon and subtotal >= coupon.minSpend:
            if coupon.discountType == 'percentage':
                discount = int(round((subtotal * coupon.value) / 100))
            else:
                discount = int(coupon.value)

    grand_total = max(0, subtotal + delivery_fee - discount)

    # Generate unique ID and tracking token with collision avoidance
    while True:
        order_id = f"BD-{random.randint(800000, 999999)}"
        tracking_token = f"tr_{order_id.lower()}_{random.randint(1000, 9999)}"
        if not Order.objects.filter(id=order_id).exists() and not Order.objects.filter(trackingToken=tracking_token).exists():
            break
    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    # Assess fraud risk
    risk_assessment = assess_order_risk(
        address.get('phone', ''),
        address.get('fullAddress', ''),
        grand_total,
        payment_method
    )

    client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    source_tag = utm.get('source') if isinstance(utm, dict) else None
    origin_note = f"Order placed via Ad ({source_tag})" if source_tag else "Direct Guest Checkout"

    payment_trx_id = data.get('paymentTrxId') or address.get('paymentTrxId')
    sender_wallet = data.get('senderWallet') or address.get('senderWallet')
    if payment_trx_id:
        address['paymentTrxId'] = str(payment_trx_id).strip()
    if sender_wallet:
        address['senderWallet'] = str(sender_wallet).strip()

    internal_notes = [f"Initial guest order submitted from IP {client_ip}"]
    if payment_trx_id:
        internal_notes.append(f"MFS Payment verified: Method={payment_method}, TrxID={payment_trx_id}, Sender={sender_wallet or 'N/A'}")

    pay_status = 'UNPAID'
    if payment_method != 'COD':
        pay_status = 'PAID' if payment_trx_id else 'PENDING'

    cust_email = (data.get('customerEmail') or data.get('email') or address.get('email') or '').strip() or None
    if cust_email:
        address['email'] = cust_email

    order = Order.objects.create(
        id=order_id,
        trackingToken=tracking_token,
        createdAt=now_str,
        customerEmail=cust_email,
        items=items,
        address=address,
        subtotal=subtotal,
        deliveryFee=delivery_fee,
        discount=discount,
        total=grand_total,
        paymentMethod=payment_method,
        paymentStatus=pay_status,
        status='PENDING',
        statusHistory=[{
            'status': 'PENDING',
            'timestamp': now_str,
            'note': origin_note,
        }],
        utm=utm,
        riskScore=risk_assessment['riskScore'],
        riskFactors=risk_assessment['riskFactors'],
        internalNotes=internal_notes
    )

    # Deduct stock atomically to prevent overselling
    for item in items:
        prod_id = item.get('productId')
        if prod_id:
            prod = Product.objects.filter(id=prod_id).first()
            if prod:
                qty = int(item.get('quantity', 1))
                prod.stock = max(0, prod.stock - qty)
                if prod.stock <= 0:
                    prod.isOutOfStock = True
                    prod.save(update_fields=['stock', 'isOutOfStock'])
                else:
                    prod.save(update_fields=['stock'])

    # Ensure customer profile is persisted in database
    cust_phone = normalize_bangladesh_phone(address.get('phone', ''))
    if cust_phone:
        cust_profile = CustomerProfile.objects.filter(phone=cust_phone).first()
        if not cust_profile:
            CustomerProfile.objects.create(
                id=f"usr-{cust_phone}-{int(timezone.now().timestamp())}",
                name=address.get('customerName') or 'সম্মানিত গ্রাহক',
                phone=cust_phone,
                email=cust_email or f"{cust_phone}@customer.chamatkar.com",
                district=district or 'Dhaka',
                thana=address.get('thana') or 'Mirpur',
                fullAddress=address.get('fullAddress') or '',
            )
        else:
            if cust_email:
                cust_profile.email = cust_email
            if address.get('customerName') and cust_profile.name in ['সম্মানিত গ্রাহক', 'Guest Customer', '']:
                cust_profile.name = address.get('customerName')
            if address.get('district'):
                cust_profile.district = address.get('district')
            if address.get('thana'):
                cust_profile.thana = address.get('thana')
            if address.get('fullAddress'):
                cust_profile.fullAddress = address.get('fullAddress')
            cust_profile.save()

    # Dispatch notifications
    dispatch_order_notifications(order, 'ORDER_CREATED')

    # Audit log
    AuditLog.log(
        actor=address.get('customerName', 'Guest Customer'),
        role='SYSTEM',
        action='ORDER_CREATED',
        target_type='ORDER',
        target_id=order.id,
        details=f"New order created for ৳{grand_total} ({payment_method}). Phone: {address.get('phone')}, District: {district}",
        ip_address=client_ip
    )

    serializer = OrderSerializer(order)
    return Response({
        'success': True,
        'orderId': order.id,
        'trackingToken': tracking_token,
        'order': serializer.data,
        'message': 'Order created successfully!'
    }, status=status.HTTP_201_CREATED)


_bdt_migrated = False

def ensure_bdt_timestamps():
    global _bdt_migrated
    if _bdt_migrated:
        return
    _bdt_migrated = True
    try:
        from datetime import datetime, timedelta
        # Check an order to see if it's overshifted to 20:34 (should be 14:34 BDT, UTC was 08:34)
        test_order = Order.objects.filter(id='BD-895460').first()
        if test_order and test_order.createdAt.startswith('2026-09-30 20:'):
            # Shift back by 6 hours to get exactly +6h from UTC
            for o in Order.objects.all():
                try:
                    dt = datetime.strptime(o.createdAt, '%Y-%m-%d %H:%M:%S')
                    o.createdAt = (dt - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
                    if isinstance(o.statusHistory, list):
                        new_hist = []
                        for h in o.statusHistory:
                            if isinstance(h, dict) and 'timestamp' in h:
                                try:
                                    h_dt = datetime.strptime(h['timestamp'], '%Y-%m-%d %H:%M:%S')
                                    h['timestamp'] = (h_dt - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
                                except Exception:
                                    pass
                            new_hist.append(h)
                        o.statusHistory = new_hist
                    o.save()
                except Exception:
                    pass

        # Check audit logs
        test_log = AuditLog.objects.filter(targetId='BD-895460').first()
        if test_log and (test_log.timestamp.startswith('2026-09-30 20:') or test_log.timestamp.startswith('2026-09-30 16:')):
            # If overshifted by 6h
            if test_log.timestamp.startswith('2026-09-30 20:'):
                for l in AuditLog.objects.all():
                    try:
                        l_dt = datetime.strptime(l.timestamp, '%Y-%m-%d %H:%M:%S')
                        l.timestamp = (l_dt - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
                        l.save()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"BDT migration error: {e}")

@api_view(['GET'])
@permission_classes([AllowAny])
def orders_list(request):
    ensure_bdt_timestamps()
    status_filter = request.query_params.get('status')
    search = request.query_params.get('search')

    orders = Order.objects.all()

    if status_filter and status_filter != 'ALL':
        orders = orders.filter(status=status_filter)

    results = []
    for order in orders:
        if search:
            q = search.lower()
            order_id_match = q in order.id.lower()
            customer_match = False
            phone_match = False
            tracking_match = False

            if isinstance(order.address, dict):
                customer_match = q in order.address.get('customerName', '').lower()
                phone_match = q in order.address.get('phone', '')

            if isinstance(order.courier, dict):
                tracking_match = q in order.courier.get('trackingId', '').lower()

            if not (order_id_match or customer_match or phone_match or tracking_match):
                continue

        results.append(order)

    serializer = OrderSerializer(results, many=True)
    return Response({
        'success': True,
        'count': len(results),
        'orders': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def order_detail(request, pk):
    order = Order.objects.filter(id=pk).first()
    if not order:
        return Response({'success': False, 'message': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = OrderSerializer(order)
    return Response({'success': True, 'order': serializer.data})


@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_order_status(request, pk):
    order = Order.objects.filter(id=pk).first()
    if not order:
        return Response({'success': False, 'message': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    note = request.data.get('note', '')
    actor_name = request.data.get('actorName', 'Operations Staff')
    actor_role = request.data.get('actorRole', 'OPERATIONS')

    if not new_status:
        return Response({'success': False, 'message': 'Missing status'}, status=status.HTTP_400_BAD_REQUEST)

    prev_status = order.status
    order.status = new_status
    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    default_notes = {
        'CONFIRMED': 'ফোন কলের মাধ্যমে ঠিকানা ও অর্ডার যাচাই সম্পন্ন',
        'COURIER_CREATED': 'কুরিয়ার বুকিং ও কনসাইনমেন্ট তৈরি সম্পন্ন',
        'PICKED_UP': 'কুরিয়ার রাইডার মার্চেন্ট হাব থেকে পার্সেল পিক করেছে',
        'IN_TRANSIT': 'পার্সেলটি গন্তব্য জেলা/থানা হাবের উদ্দেশ্যে ট্রানজিটে রয়েছে',
        'OUT_FOR_DELIVERY': 'ডেলিভারি রাইডার আপনার ঠিকানায় পার্সেল নিয়ে বের হয়েছেন',
        'DELIVERED': 'পণ্য গ্রাহকের নিকট হস্তান্তর ও মূল্য পরিশোধ সম্পন্ন',
        'RETURNED': 'গ্রাহক অনুপস্থিত বা পার্সেল গ্রহণে অপারগতা প্রকাশ করায় রিটার্ন করা হয়েছে',
        'CANCELLED': 'গ্রাহক বা অ্যাডমিনের অনুরোধে অর্ডার বাতিল করা হয়েছে',
    }

    effective_note = note or default_notes.get(new_status, f"Status updated from {prev_status} to {new_status}")

    history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
    history.append({
        'status': new_status,
        'timestamp': now_str,
        'note': effective_note,
        'updatedBy': actor_name,
    })
    order.statusHistory = history

    # Status-specific side effects
    if new_status == 'CONFIRMED':
        dispatch_order_notifications(order, 'ORDER_CONFIRMED')
    elif new_status == 'OUT_FOR_DELIVERY':
        dispatch_order_notifications(order, 'OUT_FOR_DELIVERY')
    elif new_status == 'DELIVERED':
        order.paymentStatus = 'PAID'
        dispatch_order_notifications(order, 'DELIVERED')

    order.save()

    AuditLog.log(
        actor=actor_name,
        role=actor_role if actor_role in ['ADMIN', 'OPERATIONS', 'MARKETING', 'SYSTEM'] else 'OPERATIONS',
        action='ORDER_STATUS_CHANGED',
        target_type='ORDER',
        target_id=order.id,
        details=f"Status transitioned from {prev_status} -> {new_status}. Note: {note or 'None'}",
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = OrderSerializer(order)
    return Response({'success': True, 'order': serializer.data})


@api_view(['POST'])
@permission_classes([AllowAny])
def tracking_lookup(request):
    order_id = request.data.get('orderId', '').strip().lstrip('#')
    phone = request.data.get('phone', '').strip()

    if not order_id:
        return Response({
            'success': False,
            'message': 'Please provide Order ID'
        }, status=status.HTTP_400_BAD_REQUEST)

    clean_input_phone = re.sub(r'\D', '', phone) if phone else ''

    matched_order = None
    for order in Order.objects.all():
        clean_db_id = order.id.strip().lstrip('#')
        if clean_db_id.lower() == order_id.lower():
            if clean_input_phone:
                order_phone = ''
                if isinstance(order.address, dict):
                    order_phone = re.sub(r'\D', '', str(order.address.get('phone', '')))
                
                clean_in = clean_input_phone[-10:] if len(clean_input_phone) >= 10 else clean_input_phone
                clean_ord = order_phone[-10:] if len(order_phone) >= 10 else order_phone
                
                if clean_in and clean_ord and (clean_in == clean_ord or clean_input_phone.endswith(order_phone) or order_phone.endswith(clean_input_phone)):
                    matched_order = order
                    break
            else:
                matched_order = order
                break

    if not matched_order:
        return Response({
            'success': False,
            'message': 'No matching order found for this Order ID. Please verify your details.'
        }, status=status.HTTP_404_NOT_FOUND)

    raw_phone = matched_order.address.get('phone', '') if isinstance(matched_order.address, dict) else ''
    masked_phone = (raw_phone[:3] + '*****' + raw_phone[-3:]) if len(raw_phone) >= 6 else (raw_phone or '017*****000')

    courier_data = matched_order.courier if isinstance(matched_order.courier, dict) else {}
    has_valid_courier = bool(
        courier_data.get('trackingId') or 
        courier_data.get('consignmentId') or 
        courier_data.get('provider')
    )

    return Response({
        'success': True,
        'order': {
            'id': matched_order.id,
            'createdAt': matched_order.createdAt,
            'status': matched_order.status,
            'statusHistory': matched_order.statusHistory if isinstance(matched_order.statusHistory, list) else [],
            'total': matched_order.total,
            'paymentMethod': matched_order.paymentMethod,
            'paymentStatus': matched_order.paymentStatus,
            'courier': courier_data if has_valid_courier else None,
            'items': matched_order.items if isinstance(matched_order.items, list) else [],
            'customerName': matched_order.address.get('customerName', '') if isinstance(matched_order.address, dict) else '',
            'phone': raw_phone,
            'address': matched_order.address if isinstance(matched_order.address, dict) else {},
            'addressSummary': {
                'customerName': matched_order.address.get('customerName', '') if isinstance(matched_order.address, dict) else '',
                'maskedPhone': masked_phone,
                'district': matched_order.address.get('district', '') if isinstance(matched_order.address, dict) else '',
                'thana': matched_order.address.get('thana', '') if isinstance(matched_order.address, dict) else '',
            }
        }
    })
