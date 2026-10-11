import io
import sys
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.management import call_command

@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    return Response({
        'status': 'healthy',
        'platform': 'AmarDokan - Chomotkar Native E-Commerce Core',
        'version': '1.0.0',
        'endpoints': {
            'products': '/api/v1/products',
            'orders': '/api/v1/orders',
            'checkout': '/api/v1/checkout',
            'couriers': '/api/v1/couriers',
            'tracking': '/api/v1/tracking/lookup',
            'users': '/api/v1/users',
            'system_migrate': '/api/v1/system/migrate',
        }
    })

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def trigger_migration(request):
    """
    On-demand database migration and initial data seeding endpoint.
    Allows easy one-click migration directly via browser on Render or any cloud host.
    """
    out_migrate = io.StringIO()
    out_seed = io.StringIO()
    try:
        call_command('migrate', interactive=False, stdout=out_migrate)
        migrate_log = out_migrate.getvalue()

        call_command('seed_data', interactive=False, stdout=out_seed)
        seed_log = out_seed.getvalue()

        return Response({
            'success': True,
            'message': 'ডাটাবেজ মাইগ্রেশন ও প্রাথমিক ডাটা সফলভাবে যুক্ত হয়েছে!',
            'migrate_log': migrate_log,
            'seed_log': seed_log,
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'মাইগ্রেশন ব্যর্থ হয়েছে: {str(e)}',
            'error': str(e),
            'partial_log': out_migrate.getvalue(),
        }, status=500)
