import os
from django.core.management.base import BaseCommand
from products.models import Product, Coupon, Review
from couriers.models import CourierConfig
from order.models import Order
from core.models import AuditLog, MarketingEvent, NotificationLog

class Command(BaseCommand):
    help = 'Seeds initial Chamatkar database with Bangladesh native products, couriers, and configs'

    def handle(self, *args, **kwargs):
        self.stdout.write("Ensuring core demo products exist...")

        products_data = [
            {
                'id': 'prod-1',
                'name': '360° Rotating Makeup Brush Organizer',
                'nameBn': '৩৬০° রোটেটিং মেকআপ ব্রাশ ও কসমেটিক অর্গানাইজার',
                'slug': '360-rotating-makeup-brush-organizer',
                'category': 'Beauty & Organizer',
                'price': 790,
                'regularPrice': 1250,
                'sku': 'ORG-360-BRUSH',
                'stock': 35,
                'badge': 'হট সেলিং',
                'images': [
                    '/src/assets/rotating_makeup_brush_holder.jpg',
                ],
                'description': '৩৬০° স্মুথ রোটেশন ও এয়ার-টাইট ডাস্টপ্রুফ কভার সহ লাক্সারি ক্রিস্টাল-ক্লিয়ার মেকআপ অর্গানাইজার। আপনার ড্রেসিং টেবিলকে দেবে আকর্ষণীয় ভ্যানিটি লুক।',
                'features': [
                    '৩৬০° স্মুথ সাইলেন্ট বল-বেয়ারিং ঘূর্ণন',
                    'এয়ার-টাইট ডাস্টপ্রুফ ও ওয়াটারপ্রুফ স্বচ্ছ এক্রাইলিক ঢাকনা',
                    '৭টি সেপারেট স্লট ছোট-বড় সব ধরণের ব্রাশ ও মেকআপ টুলের জন্য',
                    'প্রিমিয়াম শ্যাটারপ্রুফ ABS ও ক্রিস্টাল ডোম ফিনিশ',
                ],
                'variants': [
                    {'name': 'কালার', 'options': ['ক্লাসিক হোয়াইট', 'রয়েল এমারেল্ড', 'রোজ পিঙ্ক'], 'stock': 35},
                ],
                'rating': 4.9,
                'reviewsCount': 148,
                'isHotDeal': True,
                'warranty': '৭ দিনের রিপ্লেসমেন্ট গ্যারান্টি',
                'deliveryDays': '২৪-৪৮ ঘণ্টার মধ্যে সারা দেশে ডেলিভারি',
            },
            {
                'id': 'prod-2',
                'name': 'Vintage Rechargeable Retro Camping Lantern',
                'nameBn': 'ভিন্টেজ রিচার্জেবল রেট্রো ক্যাম্পিং লণ্ঠন',
                'slug': 'retro-rechargeable-camping-lantern',
                'category': 'Lifestyle & Outdoor',
                'price': 990,
                'regularPrice': 1550,
                'sku': 'LGT-RETRO-CAMP',
                'stock': 28,
                'badge': 'টপ রেটেড',
                'images': [
                    '/src/assets/retro_camping_lantern.jpg',
                ],
                'video360': '/src/assets/360_assets/Retro%20Rechargeable%20Camping%20Lantern.mp4',
                'description': 'ক্লাসিক ভিন্টেজ লুক ও আধুনিক ওয়ার্ম এলইডি লাইটিংয়ের এক অনন্য মেলবন্ধন। রোটারি ডিমার ও টাইপ-সি রিচার্জেবল ব্যাটারি সহ ক্যাম্পিং ও ঘরের জন্য সেরা।',
                'features': [
                    'চোখের জন্য আরামদায়ক সফট ওয়ার্ম এলইডি ফিলামেন্ট লাইট',
                    'স্টেপলেস স্মুথ রোটারি ডিমার নব দিয়ে ব্রাইটনেস নিয়ন্ত্রণ',
                    'ইউএসবি টাইপ-সি রিচার্জেবল প্রযুক্তি ও লং ব্যাকআপ',
                    'ম্যাট স্কার্লেট রেড ফিনিশ ও শক্ত মেটাল হ্যাঙ্গিং হুক',
                ],
                'variants': [
                    {'name': 'কালার', 'options': ['ভিন্টেজ রেড', 'মেটালিক ব্ল্যাক', 'আর্মি গ্রিন'], 'stock': 28},
                ],
                'rating': 4.8,
                'reviewsCount': 92,
                'isHotDeal': True,
                'warranty': '৭ দিনের রিপ্লেসমেন্ট গ্যারান্টি',
                'deliveryDays': '২৪-৪৮ ঘণ্টার মধ্যে হোম ডেলিভারি',
            },
            {
                'id': 'prod-3',
                'name': '7-in-1 Professional Nail & Manicure/Pedicure Kit',
                'nameBn': '৭-ইন-১ প্রফেশনাল নেইল ও ম্যানিকিউর/পেডিকিউর কিট',
                'slug': '7-in-1-nail-manicure-pedicure-kit',
                'category': 'Personal Care',
                'price': 490,
                'regularPrice': 850,
                'sku': 'KIT-7IN1-NAIL',
                'stock': 50,
                'badge': 'ভ্যালু ডিল',
                'images': [
                    '/src/assets/7in1_nail_manicure_kit.jpg',
                ],
                'video360': '/src/assets/360_assets/7%20in%201%20Nail%20Manicure%20%26%20Pedicure%20Kit.mp4',
                'description': 'সার্জিক্যাল গ্রেড স্টেইনলেস স্টিল ও আল্ট্রা-শার্প ব্লেড সমন্বিত ৭-ইন-১ পার্সোনাল নেইল গ্রুমিং সেট। সাথে লাক্সারি পোর্টেবল ট্রাভেল কেস।',
                'features': [
                    '৭টি প্রয়োজনীয় প্রফেশনাল গ্রুমিং টুলস এক কমপ্যাক্ট বক্সে',
                    '১০০% মরিচারোধক প্রিমিয়াম সার্জিক্যাল স্টেইনলেস স্টিল',
                    'আল্ট্রা-শার্প প্রিসিশন ব্লেড দিয়ে মসৃণ ও পেইন-ফ্রি কাটিং',
                    'লাক্সারি লেদারেট ট্রাভেল কেস সহজে বহনের জন্য',
                ],
                'variants': [
                    {'name': 'কেস কালার', 'options': ['রয়েল মেরুন', 'ক্লাসিক ক্রিম', 'ল্যাভেন্ডার'], 'stock': 50},
                ],
                'rating': 4.8,
                'reviewsCount': 112,
                'isHotDeal': True,
                'warranty': '৭ দিনের রিপ্লেসমেন্ট গ্যারান্টি',
                'deliveryDays': '২৪-৪৮ ঘণ্টার মধ্যে হোম ডেলিভারি',
            },
            {
                'id': 'prod-4',
                'name': 'Deep Tissue Electric Massage Gun',
                'nameBn': 'ডিপ টিস্যু ইলেকট্রিক ম্যাসেজ গান',
                'slug': 'facial-massage-gun-light-age',
                'category': 'Health & Wellness',
                'price': 1550,
                'regularPrice': 2400,
                'sku': 'MSG-GUN-LGT',
                'stock': 20,
                'badge': 'বেস্ট সেলার',
                'images': [
                    '/src/assets/facial_massage_gun_light_age.jpg',
                ],
                'description': 'পাওয়ারফুল সাইলেন্ট ব্রাশলেস মোটর, ৬-লেভেল স্পিড কন্ট্রোল এবং ৪টি স্পেশাল ম্যাসেজ হেড সমন্বিত "Light Age" এরগনোমিক ডিপ টিস্যু ম্যাসেজার।',
                'features': [
                    '২৪ ওয়াট হাই-টর্ক সুপার সাইলেন্ট ব্রাশলেস মোটর প্রযুক্তি',
                    '৬টি অ্যাডজাস্টেবল স্পিড ও ভাইব্রেশন লেভেল',
                    '৪টি মাল্টি-ফাংশনাল ইন্টারচেঞ্জেবল ম্যাসেজ হেড (Ball, Fork, Flat, Bullet)',
                    'টাইপ-সি ফাস্ট চার্জিং ও দীর্ঘস্থায়ী কর্ডলেস পোর্টেবিলিটি',
                ],
                'variants': [
                    {'name': 'কালার', 'options': ['আইভরি ক্রিম', 'ক্লাসিক ব্ল্যাক'], 'stock': 20},
                ],
                'rating': 4.9,
                'reviewsCount': 88,
                'isHotDeal': True,
                'warranty': '৭ দিনের রিপ্লেসমেন্ট ও ১ বছর সার্ভিস সাপোর্ট',
                'deliveryDays': '২৪-৪৮ ঘণ্টার মধ্যে সারা দেশে ডেলিভারি',
            },
        ]

        for p in products_data:
            Product.objects.update_or_create(id=p['id'], defaults=p)

        self.stdout.write("Seeding Coupons...")
        coupons = [
            {'code': 'WELCOME50', 'discountType': 'fixed', 'value': 50, 'minSpend': 500, 'isActive': True},
            {'code': 'EID100', 'discountType': 'fixed', 'value': 100, 'minSpend': 1200, 'isActive': True},
            {'code': 'SAVE10', 'discountType': 'percentage', 'value': 10, 'minSpend': 2000, 'isActive': True},
        ]
        for c in coupons:
            Coupon.objects.update_or_create(code=c['code'], defaults=c)

        self.stdout.write("Seeding Courier Configs...")
        couriers = [
            {
                'id': 'pathao',
                'name': 'Pathao Courier',
                'logo': 'Pathao',
                'isActive': True,
                'apiKey': 'pk_live_pathao_merchant_92813',
                'secret': 'ps_secret_key_847192738',
                'coverage': '64 Districts (Full BD)',
                'codFeePercent': 1.0,
                'insideDhakaRate': 60,
                'outsideDhakaRate': 130,
                'lastSyncTime': '2026-09-22 10:45 AM',
                'pendingCodAmount': 38450,
                'settledCodAmount': 184500,
            },
            {
                'id': 'steadfast',
                'name': 'Steadfast Courier',
                'logo': 'Steadfast',
                'isActive': True,
                'apiKey': os.getenv('STEADFAST_API_KEY', 'stf_live_api_88492010'),
                'secret': os.getenv('STEADFAST_SECRET_KEY', 'stf_sec_019283849'),
                'coverage': 'Nationwide & Remote Upazila',
                'codFeePercent': 1.0,
                'insideDhakaRate': 60,
                'outsideDhakaRate': 120,
                'lastSyncTime': '2026-09-22 10:50 AM',
                'pendingCodAmount': 54200,
                'settledCodAmount': 249000,
            },
            {
                'id': 'redx',
                'name': 'RedX Logistics',
                'logo': 'RedX',
                'isActive': True,
                'apiKey': os.getenv('REDX_API_TOKEN', 'redx_token_live_738192'),
                'secret': os.getenv('REDX_SECRET_KEY', 'redx_hash_918237'),
                'coverage': 'All Metros & District Towns',
                'codFeePercent': 1.0,
                'insideDhakaRate': 65,
                'outsideDhakaRate': 130,
                'lastSyncTime': '2026-09-22 09:30 AM',
                'pendingCodAmount': 16800,
                'settledCodAmount': 92400,
            },
            {
                'id': 'ecourier',
                'name': 'eCourier Limited',
                'logo': 'eCourier',
                'isActive': False,
                'apiKey': os.getenv('ECOURIER_API_KEY', 'ec_usr_849201'),
                'secret': os.getenv('ECOURIER_SECRET_KEY', 'ec_key_192837'),
                'coverage': 'Nationwide Corporate Hubs',
                'codFeePercent': 1.5,
                'insideDhakaRate': 70,
                'outsideDhakaRate': 140,
                'lastSyncTime': '2026-09-21 06:15 PM',
                'pendingCodAmount': 0,
                'settledCodAmount': 45000,
            },
        ]
        for cr in couriers:
            CourierConfig.objects.update_or_create(id=cr['id'], defaults=cr)

        self.stdout.write("Seeding Initial Order...")
        order_data = {
            'id': 'BD-849201',
            'trackingToken': 'tr_849201_99a',
            'createdAt': '2026-09-22 09:30:15',
            'items': [
                {
                    'id': 'item-1',
                    'productId': 'prod-1',
                    'name': 'T900 Ultra 2 Smartwatch with Gesture Control',
                    'nameBn': 'টি৯০০ আল্ট্রা ২ স্মার্টওয়াচ',
                    'sku': 'SMW-T900-BLK',
                    'variant': 'Orange Strap',
                    'price': 1850,
                    'quantity': 1,
                    'image': 'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=400&q=80',
                },
            ],
            'address': {
                'customerName': 'Zakir Hossain',
                'phone': '01712849201',
                'district': 'Dhaka',
                'thana': 'Mirpur-10',
                'fullAddress': 'House 14, Road 5, Block C, Section 10, Mirpur, Dhaka',
                'deliveryZone': 'inside_dhaka',
                'orderNote': 'Call before delivery please',
            },
            'subtotal': 1850,
            'deliveryFee': 60,
            'discount': 0,
            'total': 1910,
            'paymentMethod': 'COD',
            'paymentStatus': 'UNPAID',
            'status': 'COURIER_CREATED',
            'statusHistory': [
                {'status': 'PENDING', 'timestamp': '2026-09-22 09:30:15', 'note': 'Customer placed guest order'},
                {'status': 'CONFIRMED', 'timestamp': '2026-09-22 09:42:00', 'note': 'Address verified via phone call'},
                {'status': 'COURIER_CREATED', 'timestamp': '2026-09-22 10:00:22', 'note': 'Steadfast consignment booked'},
            ],
            'courier': {
                'provider': 'steadfast',
                'trackingId': 'STDF-88492019',
                'consignmentId': 'CNS-9481920',
                'courierStatus': 'Pickup Request Accepted',
                'createdDate': '2026-09-22 10:00 AM',
                'deliveryFee': 60,
                'codAmount': 1910,
                'trackingUrl': 'https://steadfast.com.bd/tracking/STDF-88492019',
                'assignedRiderName': 'Ashraful Alam',
                'assignedRiderPhone': '01811234910',
            },
            'riskScore': 12,
            'riskFactors': ['Verified Grameenphone SIM'],
            'internalNotes': ['Customer confirmed availability tomorrow afternoon.'],
        }
        Order.objects.update_or_create(id=order_data['id'], defaults=order_data)

        self.stdout.write("Seeding Audit Logs & Notifications...")
        AuditLog.objects.get_or_create(
            id='aud-1',
            defaults={
                'timestamp': '2026-09-22 10:45:12',
                'actor': 'System / Webhook',
                'role': 'SYSTEM',
                'action': 'COURIER_STATUS_UPDATE',
                'targetType': 'ORDER',
                'targetId': 'BD-849188',
                'details': 'Pathao Webhook status changed to DELIVERED. COD collection: ৳2,250.',
                'ipAddress': '103.114.98.22',
            }
        )

        NotificationLog.objects.get_or_create(
            id='notif-1',
            defaults={
                'orderId': 'BD-849201',
                'channel': 'SMS',
                'recipient': '01712849201',
                'templateName': 'ORDER_CONFIRMED',
                'messageText': 'Chamatkar: Dear Zakir Hossain, order #BD-849201 of ৳1,910 is confirmed! Your parcel is being packed. Helpline: 09612345678',
                'status': 'DELIVERED',
                'timestamp': '2026-09-22 09:42:10',
                'provider': 'Greenweb_SMS',
            }
        )


        self.stdout.write("Ensuring Django Admin Superuser exists...")
        admin_username = os.getenv('ADMIN_USER', 'admin')
        admin_password = os.getenv('ADMIN_PASS', 'admin1234')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@chamatkar.com')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                'email': admin_email,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        user.set_password(admin_password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{admin_username}' created successfully!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{admin_username}' credentials updated successfully!"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
