"""
WSGI config for chamatkar_core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chomotkar.settings')

application = get_wsgi_application()

# Automatically ensure database tables and migrations are up to date on boot (Render / Production)
try:
    from django.core.management import call_command
    print("[Chamatkar WSGI] Checking and applying database migrations...")
    call_command('migrate', interactive=False)
    print("[Chamatkar WSGI] Database migrations applied successfully.")

    # Auto-seed core demo products and configurations if table is empty
    try:
        from products.models import Product
        if Product.objects.count() == 0:
            print("[Chamatkar WSGI] No products found in database. Running seed_data...")
            call_command('seed_data', interactive=False)
            print("[Chamatkar WSGI] Initial demo data seeded successfully.")
    except Exception as seed_err:
        print(f"[Chamatkar WSGI] Notice on seed data: {seed_err}", file=sys.stderr)

except Exception as err:
    print(f"[Chamatkar WSGI] Warning: Auto-migration on boot: {err}", file=sys.stderr)
