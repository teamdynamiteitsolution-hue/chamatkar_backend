import os
import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from .models import CustomerProfile
from order.models import Order
from order.serializers import OrderSerializer


def normalize_phone(phone_str):
    if not phone_str:
        return ''
    digits = re.sub(r'\D', '', str(phone_str))
    if digits.startswith('880'):
        digits = digits[2:]
    elif not digits.startswith('0') and len(digits) >= 10:
        digits = '0' + digits
    return digits


@api_view(['POST'])
@permission_classes([AllowAny])
def user_login_or_register(request):
    data = request.data or {}
    action = data.get('action', '').strip().lower()
    raw_identifier = str(data.get('phone') or data.get('identifier') or '').strip()
    clean_phone = normalize_phone(raw_identifier)
    password = str(data.get('password') or '').strip()
    name = str(data.get('name') or 'সম্মানিত গ্রাহক').strip()
    email = data.get('email', '').strip() or None
    full_address = str(data.get('fullAddress') or '').strip()
    district = str(data.get('district') or 'Dhaka').strip()
    thana = str(data.get('thana') or 'Mirpur').strip()

    # Special handling for Demo User login
    demo_phone = os.getenv('DEMO_USER_PHONE', '01712345678')
    demo_pass = os.getenv('DEMO_USER_PASS', '1234')
    if action == 'demo' or (clean_phone == demo_phone and action != 'register'):
        demo_profile = CustomerProfile.objects.filter(phone=demo_phone).first()
        if not demo_profile:
            demo_profile = CustomerProfile.objects.create(
                id=f'usr-demo-{demo_phone}',
                name='কবিরুল ইসলাম',
                phone=demo_phone,
                email='kabir@gmail.com',
                district='Dhaka',
                thana='Dhanmondi',
                fullAddress='বাড়ি ১২, রোড ৪/এ, ধানমন্ডি, ঢাকা',
                password=make_password(demo_pass),
            )
        return Response({
            'success': True,
            'message': 'কবিরুল ইসলাম হিসেবে সফলভাবে প্রবেশ করেছেন!',
            'user': {
                'id': demo_profile.id,
                'name': demo_profile.name,
                'phone': demo_profile.phone,
                'email': demo_profile.email,
                'district': demo_profile.district,
                'thana': demo_profile.thana,
                'fullAddress': demo_profile.fullAddress,
            }
        })

    # Registration Flow
    if action == 'register':
        if not clean_phone or len(clean_phone) < 11:
            return Response(
                {'success': False, 'message': 'সঠিক ১১ ডিজিটের মোবাইল নম্বর লিখুন (যেমন: 017XXXXXXXX)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not name or name == 'সম্মানিত গ্রাহক':
            return Response(
                {'success': False, 'message': 'আপনার পূর্ণ নাম লিখুন'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not password or len(password) < 4:
            return Response(
                {'success': False, 'message': 'পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে'},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing = CustomerProfile.objects.filter(phone=clean_phone).first()
        if not existing and len(clean_phone) >= 10:
            existing = CustomerProfile.objects.filter(phone__endswith=clean_phone[-10:]).first()

        if existing:
            if not existing.password:
                # User profile was auto-created during guest order, activate with password
                existing.name = name
                if email:
                    existing.email = email
                if district:
                    existing.district = district
                if thana:
                    existing.thana = thana
                if full_address:
                    existing.fullAddress = full_address
                existing.password = make_password(password)
                existing.save()
                return Response({
                    'success': True,
                    'message': 'আপনার একাউন্ট সফলভাবে সক্রিয় ও নিবন্ধিত হয়েছে!',
                    'user': {
                        'id': existing.id,
                        'name': existing.name,
                        'phone': existing.phone,
                        'email': existing.email,
                        'district': existing.district,
                        'thana': existing.thana,
                        'fullAddress': existing.fullAddress,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'success': False, 'message': 'এই মোবাইল নম্বর দিয়ে ইতোমধ্যে একাউন্ট খোলা আছে। অনুগ্রহ করে লগইন করুন।'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        profile = CustomerProfile.objects.create(
            id=f"usr-{clean_phone}-{int(timezone.now().timestamp())}",
            name=name,
            phone=clean_phone,
            email=email or f"{clean_phone}@customer.chamatkar.com",
            district=district,
            thana=thana,
            fullAddress=full_address,
            password=make_password(password),
        )

        return Response({
            'success': True,
            'message': 'আপনার একাউন্ট সফলভাবে নিবন্ধিত হয়েছে!',
            'user': {
                'id': profile.id,
                'name': profile.name,
                'phone': profile.phone,
                'email': profile.email,
                'district': profile.district,
                'thana': profile.thana,
                'fullAddress': profile.fullAddress,
            }
        }, status=status.HTTP_201_CREATED)

    # Login Flow
    profile = None
    if '@' in raw_identifier:
        profile = CustomerProfile.objects.filter(email__iexact=raw_identifier).first()

    if not profile and clean_phone:
        profile = CustomerProfile.objects.filter(phone=clean_phone).first()
        if not profile and len(clean_phone) >= 10:
            profile = CustomerProfile.objects.filter(phone__endswith=clean_phone[-10:]).first()

    if not profile:
        return Response(
            {'success': False, 'message': 'এই মোবাইল নম্বর বা ইমেইলে কোনো একাউন্ট পাওয়া যায়নি। অনুগ্রহ করে সঠিক তথ্য দিন অথবা নতুন একাউন্ট খুলুন।'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate password if user set a password
    if profile.password:
        if not password or not check_password(password, profile.password):
            return Response(
                {'success': False, 'message': 'ভুল পাসওয়ার্ড। অনুগ্রহ করে সঠিক পাসওয়ার্ড প্রদান করুন।'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Profile exists from guest order without password set yet, set it now
        if password and len(password) >= 4:
            profile.password = make_password(password)
            profile.save()

    return Response({
        'success': True,
        'message': 'সফলভাবে লগইন হয়েছে!',
        'user': {
            'id': profile.id,
            'name': profile.name,
            'phone': profile.phone,
            'email': profile.email or f"{profile.phone}@customer.chamatkar.com",
            'district': profile.district or 'Dhaka',
            'thana': profile.thana or 'Mirpur',
            'fullAddress': profile.fullAddress or '',
        }
    })


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([AllowAny])
def user_profile(request, phone):
    clean = normalize_phone(phone)
    profile = CustomerProfile.objects.filter(phone=clean).first()
    if not profile and len(clean) >= 10:
        profile = CustomerProfile.objects.filter(phone__endswith=clean[-10:]).first()

    if not profile:
        return Response({'success': False, 'message': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method in ['PUT', 'PATCH']:
        data = request.data
        if 'name' in data and data['name']:
            profile.name = str(data['name']).strip()
        if 'email' in data:
            profile.email = str(data['email']).strip() or None
        if 'district' in data and data['district']:
            profile.district = str(data['district']).strip()
        if 'thana' in data and data['thana']:
            profile.thana = str(data['thana']).strip()
        if 'fullAddress' in data:
            profile.fullAddress = str(data['fullAddress']).strip()
        profile.save()

    return Response({
        'success': True,
        'user': {
            'id': profile.id,
            'name': profile.name,
            'phone': profile.phone,
            'email': profile.email,
            'district': profile.district,
            'thana': profile.thana,
            'fullAddress': profile.fullAddress,
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def customer_orders(request, phone):
    clean = normalize_phone(phone)
    if not clean or len(clean) < 6:
        return Response({'success': False, 'orders': [], 'message': 'Invalid phone'}, status=status.HTTP_400_BAD_REQUEST)

    matched_orders = []
    for order in Order.objects.all():
        if isinstance(order.address, dict):
            ord_phone = normalize_phone(order.address.get('phone', ''))
            if ord_phone and (ord_phone.endswith(clean[-10:]) or clean.endswith(ord_phone[-10:])):
                matched_orders.append(order)

    serializer = OrderSerializer(matched_orders, many=True)
    return Response({
        'success': True,
        'orders': serializer.data,
        'total': len(matched_orders)
    })
