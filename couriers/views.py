from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import CourierConfig
from .serializers import CourierConfigSerializer
from .adapters import courier_adapters
from order.models import Order
from order.serializers import OrderSerializer
from order.services import dispatch_order_notifications
from core.models import AuditLog

@api_view(['GET'])
@permission_classes([AllowAny])
def couriers_list(request):
    configs = CourierConfig.objects.all()
    serializer = CourierConfigSerializer(configs, many=True)
    return Response({'success': True, 'couriers': serializer.data})


@api_view(['PUT'])
@permission_classes([AllowAny])
def courier_update(request, pk):
    config = CourierConfig.objects.filter(id=pk).first()
    if not config:
        return Response({'success': False, 'message': 'Courier not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = CourierConfigSerializer(config, data=request.data, partial=True)
    if serializer.is_valid():
        config = serializer.save()
        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='COURIER_CONFIG_UPDATED',
            target_type='SETTINGS',
            target_id=config.id,
            details=f"Updated courier settings for {config.id}",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response({'success': True, 'courier': serializer.data})
    return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def assign_courier(request):
    data = request.data
    order_id = data.get('orderId')
    provider = data.get('provider', '').lower()
    weight_kg = float(data.get('weightKg') or 0.5)
    special_instruction = data.get('specialInstruction') or data.get('instructions') or ''
    actor_name = data.get('actorName', 'Operations Staff')

    order = Order.objects.filter(id=order_id).first()
    if not order:
        return Response({'success': False, 'message': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    adapter = courier_adapters.get(provider)
    if not adapter:
        return Response({'success': False, 'message': f"Unsupported courier provider: {provider}"}, status=status.HTTP_400_BAD_REQUEST)

    # Verify courier is active in CourierConfig
    courier_config = CourierConfig.objects.filter(id=provider).first()
    if courier_config and not courier_config.isActive:
        return Response({
            'success': False,
            'message': f"Courier provider '{courier_config.name}' is currently disabled in Courier Hub."
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        shipment = adapter.create_shipment(order, item_weight_kg=weight_kg, special_instruction=special_instruction)

        order.courier = shipment
        order.status = 'COURIER_CREATED'
        now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

        history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
        history.append({
            'status': 'COURIER_CREATED',
            'timestamp': now_str,
            'note': f"Assigned to {adapter.name}. Consignment: {shipment['consignmentId']}, Tracking ID: {shipment['trackingId']}",
            'updatedBy': actor_name,
        })
        order.statusHistory = history
        order.save()

        # Notify customer
        dispatch_order_notifications(order, 'SHIPMENT_CREATED')

        # Audit log
        AuditLog.log(
            actor=actor_name,
            role='OPERATIONS',
            action='COURIER_ASSIGNED',
            target_type='ORDER',
            target_id=order.id,
            details=f"Booked shipment via {adapter.name}. Consignment: {shipment['consignmentId']}",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )

        order_serializer = OrderSerializer(order)
        return Response({'success': True, 'shipment': shipment, 'order': order_serializer.data})

    except Exception as e:
        return Response({'success': False, 'message': str(e) or 'Courier booking failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def courier_balance(request, provider):
    prov = str(provider).strip().lower()
    adapter = courier_adapters.get(prov)
    if not adapter:
        return Response({'success': False, 'message': f'Courier provider {provider} not found'}, status=status.HTTP_404_NOT_FOUND)
    result = adapter.get_balance()
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def courier_check_status(request, provider, tracking_code):
    prov = str(provider).strip().lower()
    adapter = courier_adapters.get(prov)
    if not adapter:
        return Response({'success': False, 'message': f'Courier provider {provider} not found'}, status=status.HTTP_404_NOT_FOUND)
    result = adapter.check_status(tracking_code)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def steadfast_balance(request):
    return courier_balance(request, 'steadfast')


@api_view(['GET'])
@permission_classes([AllowAny])
def steadfast_check_status(request, tracking_code):
    return courier_check_status(request, 'steadfast', tracking_code)


def process_courier_webhook_data(data, ip_address='127.0.0.1'):
    provider = data.get('provider', '').lower()
    
    # Check if Steadfast specific fields exist in webhook
    if not provider and ('tracking_code' in data or 'consignment_id' in data or 'invoice' in data):
        provider = 'steadfast'
    if not provider:
        provider = 'pathao'

    invoice_val = str(
        data.get('merchant_invoice_id') or 
        data.get('merchant_order_id') or 
        data.get('invoice') or 
        data.get('order_id') or 
        data.get('orderId') or ''
    ).strip()
    tracking_val = str(data.get('tracking_code') or data.get('tracking_id') or data.get('trackingId') or '').strip()
    consignment_val = str(data.get('consignment_id') or data.get('consignmentId') or '').strip()

    if not (invoice_val or tracking_val or consignment_val):
        return {'success': False, 'message': 'Missing tracking_code, consignment_id, invoice or order_id', 'status_code': status.HTTP_400_BAD_REQUEST}

    order = None
    if invoice_val:
        order = Order.objects.filter(id__iexact=invoice_val).first()

    if not order and (tracking_val or consignment_val):
        for o in Order.objects.all():
            c = o.courier if isinstance(o.courier, dict) else {}
            c_track = str(c.get('trackingId') or '').strip().lower()
            c_cons = str(c.get('consignmentId') or '').strip().lower()
            if (tracking_val and c_track == tracking_val.lower()) or (consignment_val and c_cons == consignment_val.lower()):
                order = o
                break

    if not order:
        lookup_ref = invoice_val or tracking_val or consignment_val
        return {'success': True, 'acknowledged': True, 'message': f"Webhook acknowledged. Order not found for reference: {lookup_ref}", 'status_code': status.HTTP_200_OK}

    adapter = courier_adapters.get(provider) or courier_adapters.get('steadfast')
    if not adapter:
        adapter = courier_adapters['steadfast']

    # If order does not have courier assigned yet, generate shipment details on the fly
    if not isinstance(order.courier, dict) or not order.courier.get('trackingId'):
        order.courier = adapter.create_shipment(order)

    parsed = adapter.parse_webhook(data)

    prev_status = order.status
    order.status = parsed['orderStatus']
    
    courier_dict = dict(order.courier) if isinstance(order.courier, dict) else {}
    courier_dict['courierStatus'] = parsed['notes']
    order.courier = courier_dict

    if parsed['orderStatus'] == 'DELIVERED':
        order.paymentStatus = 'PAID'
        dispatch_order_notifications(order, 'DELIVERED')
    elif parsed['orderStatus'] == 'OUT_FOR_DELIVERY':
        dispatch_order_notifications(order, 'OUT_FOR_DELIVERY')

    now_str = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    history = list(order.statusHistory) if isinstance(order.statusHistory, list) else []
    history.append({
        'status': parsed['orderStatus'],
        'timestamp': now_str,
        'note': parsed['notes'],
        'updatedBy': f"Courier Webhook ({adapter.name})",
    })
    order.statusHistory = history
    order.save()

    AuditLog.log(
        actor=f"{adapter.name} Webhook",
        role='SYSTEM',
        action='COURIER_WEBHOOK_PROCESSED',
        target_type='ORDER',
        target_id=order.id,
        details=f"Received event: {data.get('status') or data.get('event')}. Status transitioned from {prev_status} to {parsed['orderStatus']}. Collected: ৳{parsed.get('collectedAmount', 0)}",
        ip_address=ip_address
    )

    order_serializer = OrderSerializer(order)
    return {
        'success': True,
        'status': 200,
        'message': 'Webhook processed successfully',
        'order': order_serializer.data,
        'status_code': status.HTTP_200_OK
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def steadfast_webhook(request):
    """
    Dedicated webhook endpoint for Steadfast Courier.
    Configured in Steadfast merchant panel as: https://yourdomain.com/api/v1/webhooks/couriers/steadfast
    """
    data = dict(request.data)
    data['provider'] = 'steadfast'
    result = process_courier_webhook_data(data, ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'))
    status_code = result.pop('status_code', status.HTTP_200_OK)
    return Response(result, status=status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
def provider_webhook(request, provider):
    """
    Dedicated webhook endpoint for any provider (/api/v1/webhooks/couriers/<provider>).
    Supports steadfast, pathao, redx, ecourier.
    """
    data = dict(request.data)
    data['provider'] = str(provider).strip().lower()
    result = process_courier_webhook_data(data, ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'))
    status_code = result.pop('status_code', status.HTTP_200_OK)
    return Response(result, status=status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
def courier_webhook(request):
    data = dict(request.data)
    result = process_courier_webhook_data(data, ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'))
    status_code = result.pop('status_code', status.HTTP_200_OK)
    return Response(result, status=status_code)
