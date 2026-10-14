from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils.text import slugify
import time

from .models import Product, Coupon, Review
from .serializers import ProductSerializer, CouponSerializer, ReviewSerializer
from .cloudinary_service import upload_image, delete_image, is_cloudinary_configured
from core.models import AuditLog

def auto_translate_product_data(data: dict) -> dict:
    """
    Synchronously translates all missing product content between English and Bengali:
    - name <-> nameBn
    - description <-> descriptionBn
    - shortDescription <-> shortDescriptionBn
    - features <-> featuresBn
    - featureDetails (ensures title/titleBn and description/descriptionBn)
    """
    try:
        from translator.services import translate_text, batch_translate
        import re

        has_bengali = lambda s: bool(re.search(r'[\u0980-\u09FF]', str(s or '')))
        has_english = lambda s: bool(re.search(r'[a-zA-Z]{2,}', str(s or '')))

        # 1. Product Name
        name = (data.get('name') or '').strip()
        name_bn = (data.get('nameBn') or '').strip()

        if name and not name_bn:
            if not has_bengali(name):
                data['nameBn'] = translate_text(name, 'auto', 'bn')
            else:
                data['nameBn'] = name
                data['name'] = translate_text(name, 'auto', 'en')
        elif name_bn and not name:
            if has_bengali(name_bn):
                data['name'] = translate_text(name_bn, 'auto', 'en')
            else:
                data['name'] = name_bn
                data['nameBn'] = translate_text(name_bn, 'auto', 'bn')
        elif name and name_bn and (name == name_bn or not has_bengali(name_bn)):
            if not has_bengali(name_bn):
                data['nameBn'] = translate_text(name, 'auto', 'bn')

        # 2. Short Description
        s_desc = (data.get('shortDescription') or '').strip()
        s_desc_bn = (data.get('shortDescriptionBn') or '').strip()
        if s_desc and not s_desc_bn:
            if not has_bengali(s_desc):
                data['shortDescriptionBn'] = translate_text(s_desc, 'auto', 'bn')
            else:
                data['shortDescriptionBn'] = s_desc
                data['shortDescription'] = translate_text(s_desc, 'auto', 'en')
        elif s_desc_bn and not s_desc:
            data['shortDescription'] = translate_text(s_desc_bn, 'auto', 'en')

        # 3. Full Description
        desc = (data.get('description') or '').strip()
        desc_bn = (data.get('descriptionBn') or '').strip()
        if desc and not desc_bn:
            if not has_bengali(desc):
                data['descriptionBn'] = translate_text(desc, 'auto', 'bn')
            else:
                data['descriptionBn'] = desc
                data['description'] = translate_text(desc, 'auto', 'en')
        elif desc_bn and not desc:
            data['description'] = translate_text(desc_bn, 'auto', 'en')

        # 4. Features Array
        feats = data.get('features')
        feats_bn = data.get('featuresBn')
        if isinstance(feats, list) and feats and (not feats_bn or not isinstance(feats_bn, list)):
            if any(has_english(f) for f in feats):
                data['featuresBn'] = batch_translate(feats, source_lang='auto', target_lang='bn')
            else:
                data['featuresBn'] = feats
                data['features'] = batch_translate(feats, source_lang='auto', target_lang='en')

        # 5. Feature Details (Cards)
        fd_list = data.get('featureDetails')
        if isinstance(fd_list, list) and fd_list:
            for item in fd_list:
                if not isinstance(item, dict):
                    continue
                t = (item.get('title') or '').strip()
                t_bn = (item.get('titleBn') or '').strip()
                if t and not t_bn:
                    if not has_bengali(t):
                        item['titleBn'] = translate_text(t, 'auto', 'bn')
                    else:
                        item['titleBn'] = t
                        item['title'] = translate_text(t, 'auto', 'en')
                elif t_bn and not t:
                    item['title'] = translate_text(t_bn, 'auto', 'en')

                d = (item.get('description') or '').strip()
                d_bn = (item.get('descriptionBn') or '').strip()
                if d and not d_bn:
                    if not has_bengali(d):
                        item['descriptionBn'] = translate_text(d, 'auto', 'bn')
                    else:
                        item['descriptionBn'] = d
                        item['description'] = translate_text(d, 'auto', 'en')
                elif d_bn and not d:
                    item['description'] = translate_text(d_bn, 'auto', 'en')

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Product auto-translation failed: {e}")

    return data

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def products_list_create(request):
    if request.method == 'GET':
        category = request.query_params.get('category')
        search = request.query_params.get('search')

        queryset = Product.objects.all().order_by('sortOrder', '-created_at')

        if category and category != 'All' and category != 'ALL':
            queryset = queryset.filter(category__iexact=category)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(nameBn__icontains=search) |
                Q(sku__icontains=search) |
                Q(category__icontains=search)
            )

        serializer = ProductSerializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'products': serializer.data
        })

    elif request.method == 'POST':
        data = request.data.copy()
        if not data.get('id'):
            data['id'] = f"prod-{int(time.time() * 1000)}"
        if not data.get('slug'):
            base_slug = slugify(data.get('name', '')) or f"prod-{int(time.time())}"
            data['slug'] = f"{base_slug}-{int(time.time() % 10000)}"
        if 'images' not in data and 'image' in data:
            data['images'] = [data['image']] if data['image'] else []
        elif 'images' not in data:
            data['images'] = []
        if 'regularPrice' not in data:
            data['regularPrice'] = data.get('originalPrice', data.get('price', 0))
        if 'stock' not in data:
            data['stock'] = 20
        if 'rating' not in data:
            data['rating'] = 4.8
        if 'reviewsCount' not in data:
            data['reviewsCount'] = 1
        if 'tag' in data and not data.get('badge'):
            data['badge'] = data['tag']
        if data.get('badge') in ['BESTSELLER', 'HOT_DEAL']:
            data['isHotDeal'] = True

        if data.get('productType') == 'standard':
            data['variants'] = []

        # Handle features / keyFeatures
        if 'keyFeatures' in data and ('features' not in data or not data['features']):
            kf = data['keyFeatures']
            if isinstance(kf, list):
                data['features'] = kf
            elif isinstance(kf, str):
                lines = [line.strip().lstrip('•-*1234567890. ') for line in kf.split('\n') if line.strip()]
                data['features'] = lines
        elif 'features' in data and isinstance(data['features'], str):
            lines = [line.strip().lstrip('•-*1234567890. ') for line in data['features'].split('\n') if line.strip()]
            data['features'] = lines

        if 'featureDetails' in data:
            fd = data['featureDetails']
            if isinstance(fd, str):
                import json
                try:
                    data['featureDetails'] = json.loads(fd)
                except Exception:
                    data['featureDetails'] = []
            elif not isinstance(fd, list):
                data['featureDetails'] = []

        if 'video360' in data:
            data['video360'] = str(data['video360']).strip()

        data = auto_translate_product_data(data)

        serializer = ProductSerializer(data=data)
        if serializer.is_valid():
            try:
                product = serializer.save()
                try:
                    AuditLog.log(
                        actor='Admin',
                        role='ADMIN',
                        action='PRODUCT_CREATED',
                        target_type='PRODUCT',
                        target_id=product.id,
                        details=f'Created product "{product.name}" (SKU: {product.sku}, Category: {product.category}, Stock: {product.stock})',
                        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
                except Exception as audit_err:
                    print(f"[Warning] AuditLog creation failed: {audit_err}")
                return Response({'success': True, 'product': serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as save_err:
                return Response({
                    'success': False,
                    'message': f'প্রোডাক্ট ডাটাবেজে সংরক্ষণ করা যায়নি: {str(save_err)}',
                    'error': str(save_err)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def product_detail_update(request, pk):
    try:
        product = Product.objects.filter(Q(id=pk) | Q(slug=pk)).first()
        if not product:
            return Response({'success': False, 'message': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({'success': False, 'message': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ProductSerializer(product)
        return Response({'success': True, 'product': serializer.data})

    elif request.method in ['PUT', 'PATCH']:
        data = request.data.copy()
        if 'images' not in data and 'image' in data:
            data['images'] = [data['image']] if data['image'] else []
        if 'regularPrice' not in data and 'originalPrice' in data:
            data['regularPrice'] = data['originalPrice']
        if 'slug' not in data:
            data['slug'] = product.slug
        if 'tag' in data and 'badge' not in data:
            data['badge'] = data['tag']
        if 'badge' in data and data['badge'] in ['BESTSELLER', 'HOT_DEAL']:
            data['isHotDeal'] = True
        elif 'badge' in data and data['badge'] not in ['BESTSELLER', 'HOT_DEAL']:
            data['isHotDeal'] = False

        if data.get('productType') == 'standard':
            data['variants'] = []

        # Handle features / keyFeatures
        if 'keyFeatures' in data:
            kf = data['keyFeatures']
            if isinstance(kf, list):
                data['features'] = kf
            elif isinstance(kf, str):
                lines = [line.strip().lstrip('•-*1234567890. ') for line in kf.split('\n') if line.strip()]
                data['features'] = lines
        elif 'features' in data and isinstance(data['features'], str):
            lines = [line.strip().lstrip('•-*1234567890. ') for line in data['features'].split('\n') if line.strip()]
            data['features'] = lines

        if 'featureDetails' in data:
            fd = data['featureDetails']
            if isinstance(fd, str):
                import json
                try:
                    data['featureDetails'] = json.loads(fd)
                except Exception:
                    data['featureDetails'] = []
            elif not isinstance(fd, list):
                data['featureDetails'] = []

        if 'video360' in data:
            data['video360'] = str(data['video360']).strip()

        data = auto_translate_product_data(data)

        serializer = ProductSerializer(product, data=data, partial=True)
        if serializer.is_valid():
            try:
                product = serializer.save()
                try:
                    AuditLog.log(
                        actor='Admin',
                        role='ADMIN',
                        action='PRODUCT_UPDATED',
                        target_type='PRODUCT',
                        target_id=product.id,
                        details=f'Updated product {product.id} (Stock: {product.stock}, Price: {product.price})',
                        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
                except Exception as audit_err:
                    print(f"[Warning] AuditLog creation failed: {audit_err}")
                return Response({'success': True, 'product': serializer.data})
            except Exception as save_err:
                return Response({
                    'success': False,
                    'message': f'প্রোডাক্ট আপডেট করা যায়নি: {str(save_err)}',
                    'error': str(save_err)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        prod_id = product.id
        prod_name = product.name
        # Clean up Cloudinary images if present
        if product.images and isinstance(product.images, list):
            for img_url in product.images:
                try:
                    delete_image(img_url)
                except Exception:
                    pass

        product.delete()
        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='PRODUCT_DELETED',
            target_type='PRODUCT',
            target_id=prod_id,
            details=f'Deleted product "{prod_name}" (ID: {prod_id})',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response({
            'success': True,
            'message': f'Product "{prod_name}" deleted successfully.',
            'id': prod_id
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_update_stock(request):
    """
    Bulk update product stock in database.
    Accepts:
    1) { "updates": [{ "id": "prod-1", "stock": 50 }, ...] }
    2) { "adjustment": 10, "product_ids": ["prod-1", ...] } (or all products if product_ids empty)
    3) { "set_stock": 25, "product_ids": [...] }
    """
    data = request.data
    updated_products = []

    if 'updates' in data and isinstance(data['updates'], list):
        for item in data['updates']:
            p_id = item.get('id')
            new_stock = item.get('stock')
            if p_id is not None and new_stock is not None:
                p = Product.objects.filter(id=p_id).first()
                if p:
                    p.stock = max(0, int(new_stock))
                    p.save(update_fields=['stock', 'updated_at'])
                    updated_products.append(p)

    elif 'adjustment' in data:
        adj = int(data.get('adjustment', 0))
        p_ids = data.get('product_ids', [])
        qs = Product.objects.filter(id__in=p_ids) if p_ids else Product.objects.all()
        for p in qs:
            p.stock = max(0, p.stock + adj)
            p.save(update_fields=['stock', 'updated_at'])
            updated_products.append(p)

    elif 'set_stock' in data:
        target = max(0, int(data.get('set_stock', 0)))
        p_ids = data.get('product_ids', [])
        qs = Product.objects.filter(id__in=p_ids) if p_ids else Product.objects.all()
        for p in qs:
            p.stock = target
            p.save(update_fields=['stock', 'updated_at'])
            updated_products.append(p)

    else:
        return Response({'success': False, 'message': 'Invalid bulk stock update payload'}, status=status.HTTP_400_BAD_REQUEST)

    AuditLog.log(
        actor='Admin',
        role='ADMIN',
        action='BULK_STOCK_UPDATED',
        target_type='PRODUCT',
        target_id='MULTIPLE',
        details=f'Bulk updated stock for {len(updated_products)} products',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    serializer = ProductSerializer(updated_products, many=True)
    return Response({
        'success': True,
        'count': len(updated_products),
        'products': serializer.data
    })

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_image_view(request):
    """
    Upload an image file to Cloudinary (or fallback to local media).
    """
    file_obj = request.FILES.get('image') or request.FILES.get('file')
    if not file_obj:
        return Response({
            'success': False,
            'message': 'No image file provided in request.'
        }, status=status.HTTP_400_BAD_REQUEST)

    target_folder = (request.data.get('folder') or os.getenv('CLOUDINARY_FOLDER', 'Chamatkar/products')).strip()
    res = upload_image(file_obj, folder=target_folder)
    if res.get('success'):
        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='IMAGE_UPLOADED',
            target_type='ASSET',
            target_id=res.get('public_id', 'unknown'),
            details=f"Uploaded image to {res.get('storage')} storage ({res.get('url')})",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response(res, status=status.HTTP_201_CREATED)
    else:
        return Response(res, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST', 'DELETE'])
@permission_classes([AllowAny])
def delete_image_view(request):
    """
    Delete an image from Cloudinary or local media.
    Accepts: { "public_id": "...", "url": "..." } in body or query param
    """
    public_id = request.data.get('public_id') or request.query_params.get('public_id')
    url = request.data.get('url') or request.query_params.get('url')

    target = public_id or url
    if not target:
        return Response({
            'success': False,
            'message': 'Either public_id or url must be provided.'
        }, status=status.HTTP_400_BAD_REQUEST)

    res = delete_image(target)
    if res.get('success'):
        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='IMAGE_DELETED',
            target_type='ASSET',
            target_id=str(target),
            details=f"Deleted image {target} from {res.get('storage', 'cloudinary')} storage",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response(res, status=status.HTTP_200_OK)
    else:
        return Response(res, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def coupons_list_or_create(request):
    if request.method == 'GET':
        include_all = request.query_params.get('include_all', 'false').lower() == 'true'
        if include_all:
            coupons = Coupon.objects.all().order_by('code')
        else:
            coupons = Coupon.objects.filter(isActive=True).order_by('code')
        serializer = CouponSerializer(coupons, many=True)
        return Response({'success': True, 'coupons': serializer.data})

    elif request.method == 'POST':
        data = request.data
        code = str(data.get('code', '')).strip().upper()
        if not code:
            return Response({'success': False, 'message': 'Coupon code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        discount_type = data.get('discountType', 'fixed')
        if discount_type not in ['fixed', 'percentage']:
            discount_type = 'fixed'
        
        try:
            value = int(data.get('value', 0))
            min_spend = int(data.get('minSpend', 0))
        except (ValueError, TypeError):
            return Response({'success': False, 'message': 'Value and minSpend must be numbers'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_active = bool(data.get('isActive', True))

        coupon, created = Coupon.objects.update_or_create(
            code=code,
            defaults={
                'discountType': discount_type,
                'value': value,
                'minSpend': min_spend,
                'isActive': is_active
            }
        )

        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='COUPON_CREATED' if created else 'COUPON_UPDATED',
            target_type='COUPON',
            target_id=code,
            details=f"Coupon {code} {'created' if created else 'updated'}: {discount_type} {value}, min spend {min_spend}",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )

        serializer = CouponSerializer(coupon)
        return Response({
            'success': True,
            'coupon': serializer.data,
            'message': f"Coupon {code} {'created' if created else 'updated'} successfully"
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def coupon_detail_update_delete(request, code):
    code_clean = str(code).strip().upper()
    coupon = Coupon.objects.filter(code__iexact=code_clean).first()
    if not coupon:
        return Response({'success': False, 'message': f'Coupon {code} not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CouponSerializer(coupon)
        return Response({'success': True, 'coupon': serializer.data})

    elif request.method in ['PUT', 'PATCH']:
        data = request.data
        if 'discountType' in data:
            dtype = data['discountType']
            if dtype in ['fixed', 'percentage']:
                coupon.discountType = dtype
        if 'value' in data:
            try:
                coupon.value = int(data['value'])
            except (ValueError, TypeError):
                pass
        if 'minSpend' in data:
            try:
                coupon.minSpend = int(data['minSpend'])
            except (ValueError, TypeError):
                pass
        if 'isActive' in data:
            coupon.isActive = bool(data['isActive'])

        coupon.save()

        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='COUPON_UPDATED',
            target_type='COUPON',
            target_id=coupon.code,
            details=f"Coupon {coupon.code} updated: active={coupon.isActive}, val={coupon.value}",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )

        serializer = CouponSerializer(coupon)
        return Response({'success': True, 'coupon': serializer.data, 'message': f'Coupon {coupon.code} updated successfully'})

    elif request.method == 'DELETE':
        coupon_code = coupon.code
        coupon.delete()

        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='COUPON_DELETED',
            target_type='COUPON',
            target_id=coupon_code,
            details=f"Coupon {coupon_code} deleted",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )

        return Response({'success': True, 'message': f'Coupon {coupon_code} deleted successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def reorder_products(request):
    """
    Update sort order of products from drag-and-drop.
    Accepts: { "order": ["prod-1", "prod-2", ...] }
    """
    order = request.data.get('order', [])
    if not isinstance(order, list):
        return Response({'success': False, 'message': 'order must be a list of product IDs'}, status=status.HTTP_400_BAD_REQUEST)

    for idx, prod_id in enumerate(order):
        Product.objects.filter(id=prod_id).update(sortOrder=idx)

    AuditLog.log(
        actor='Admin',
        role='ADMIN',
        action='PRODUCTS_REORDERED',
        target_type='PRODUCT',
        target_id='all',
        details=f'Reordered {len(order)} products via drag and drop',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )
    return Response({'success': True, 'message': 'Products reordered successfully', 'order': order})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def reviews_list_create(request):
    """
    GET  /api/v1/reviews - list reviews (optional filters: ?product_id=..., ?order_id=..., ?approved_only=true)
    POST /api/v1/reviews - submit new review from tracking portal or admin
    """
    if request.method == 'GET':
        queryset = Review.objects.all().order_by('-created_at')
        product_id = request.query_params.get('product_id')
        order_id = request.query_params.get('order_id')
        approved_only = request.query_params.get('approved_only', 'false').lower() in ('true', '1')

        if product_id:
            queryset = queryset.filter(
                Q(product_id=product_id) |
                Q(product__slug=product_id) |
                Q(product_name__iexact=product_id)
            )
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        if approved_only:
            queryset = queryset.filter(is_approved=True)

        # Auto-repair legacy reviews that have generic 'Customer' name by looking up their linked order
        from order.models import Order
        for r in queryset:
            if (not r.customer_name or r.customer_name.strip().lower() in ['customer', 'guest', 'সম্মানিত গ্রাহক']) and r.order_id:
                ord_obj = Order.objects.filter(id=r.order_id).first()
                if ord_obj and isinstance(ord_obj.address, dict):
                    resolved = ord_obj.address.get('customerName') or ord_obj.address.get('name')
                    if resolved:
                        r.customer_name = resolved
                        if not r.customer_phone and ord_obj.address.get('phone'):
                            r.customer_phone = ord_obj.address.get('phone')
                        if (not r.location or r.location == 'Dhaka, Bangladesh') and ord_obj.address.get('district'):
                            r.location = f"{ord_obj.address.get('district')}, Bangladesh"
                        r.save(update_fields=['customer_name', 'customer_phone', 'location'])

        serializer = ReviewSerializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'reviews': serializer.data
        })

    elif request.method == 'POST':
        data = request.data.copy()
        if not data.get('id'):
            data['id'] = f"rev-{int(time.time() * 1000)}"

        from order.models import Order
        order_id = (data.get('order_id') or '').strip()
        cust_name = (data.get('customer_name') or '').strip()

        # If customer_name is missing or generic 'Customer', auto-resolve from linked Order
        if not cust_name or cust_name.lower() in ['customer', 'guest', 'সম্মানিত গ্রাহক']:
            if order_id:
                ord_obj = Order.objects.filter(id=order_id).first()
                if ord_obj and isinstance(ord_obj.address, dict):
                    resolved_name = (
                        ord_obj.address.get('customerName') or
                        ord_obj.address.get('name') or
                        ord_obj.address.get('recipient_name')
                    )
                    if resolved_name:
                        data['customer_name'] = resolved_name
                        cust_name = resolved_name
                    if not data.get('customer_phone') and ord_obj.address.get('phone'):
                        data['customer_phone'] = ord_obj.address.get('phone')
                    if (not data.get('location') or data.get('location') == 'Dhaka, Bangladesh') and ord_obj.address.get('district'):
                        dist = ord_obj.address.get('district')
                        thana = ord_obj.address.get('thana')
                        loc = f"{dist}, Bangladesh" if not thana else f"{thana}, {dist}"
                        data['location'] = loc
                    if not data.get('product_name') and ord_obj.items:
                        first_item = ord_obj.items[0] if isinstance(ord_obj.items, list) and len(ord_obj.items) > 0 else {}
                        data['product_name'] = first_item.get('name', '')
                        if not data.get('product') and first_item.get('productId'):
                            data['product'] = first_item.get('productId')

        # Fallback if still generic
        if not data.get('customer_name') or data.get('customer_name').strip().lower() in ['customer', 'guest']:
            data['customer_name'] = 'ভেরিফাইড ক্রেতা'

        # Validate rating 1..5
        try:
            rating_val = int(data.get('rating', 5))
            data['rating'] = max(1, min(5, rating_val))
        except (ValueError, TypeError):
            data['rating'] = 5

        # If product is specified, safely link to existing Product or fallback gracefully
        if data.get('product'):
            prod = Product.objects.filter(Q(id=data['product']) | Q(slug=data['product'])).first()
            if prod:
                data['product'] = prod.id
                if not data.get('product_name'):
                    data['product_name'] = prod.name
            else:
                data['product'] = None

        serializer = ReviewSerializer(data=data)
        if serializer.is_valid():
            review = serializer.save()

            # Update product rating and reviewsCount if attached to a product
            if review.product:
                prod = review.product
                approved_reviews = Review.objects.filter(product=prod, is_approved=True)
                if approved_reviews.exists():
                    avg_rating = sum(r.rating for r in approved_reviews) / approved_reviews.count()
                    prod.rating = round(avg_rating, 1)
                    prod.reviewsCount = approved_reviews.count()
                    prod.save(update_fields=['rating', 'reviewsCount'])

            AuditLog.log(
                actor=data.get('customer_name') or 'Customer',
                role='CUSTOMER' if data.get('source') != 'ADMIN_MANUAL' else 'ADMIN',
                action='REVIEW_SUBMITTED',
                target_type='REVIEW',
                target_id=review.id,
                details=f"New {review.rating}★ review by {review.customer_name} ({review.source})",
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            return Response({'success': True, 'review': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE', 'PATCH'])
@permission_classes([AllowAny])
def review_detail_update_delete(request, pk):
    """
    GET, PUT, PATCH, DELETE /api/v1/reviews/<pk>
    """
    try:
        review = Review.objects.get(id=pk)
    except Review.DoesNotExist:
        return Response({'success': False, 'message': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ReviewSerializer(review)
        return Response({'success': True, 'review': serializer.data})

    elif request.method in ['PUT', 'PATCH']:
        serializer = ReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            updated_review = serializer.save()
            return Response({'success': True, 'review': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        review_id = review.id
        review.delete()
        AuditLog.log(
            actor='Admin',
            role='ADMIN',
            action='REVIEW_DELETED',
            target_type='REVIEW',
            target_id=review_id,
            details=f"Review {review_id} deleted",
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        return Response({'success': True, 'message': 'Review deleted successfully'})

