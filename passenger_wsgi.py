"""
Phusion Passenger WSGI entry point for cPanel Shared Hosting.
This file explicitly loads the virtual environment site-packages and initializes Django.
"""
import os
import sys

# 1. Add Virtualenv site-packages so Passenger uses all installed libraries (Django, etc.)
VENV_PACKAGES = '/home13/chamatkar/virtualenv/chamatkar_backend/3.10/lib/python3.10/site-packages'
if os.path.exists(VENV_PACKAGES) and VENV_PACKAGES not in sys.path:
    sys.path.insert(0, VENV_PACKAGES)

# 2. Add Application Root to sys.path
APP_ROOT = '/home13/chamatkar/chamatkar_backend'
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# 3. Enable PyMySQL as MySQLdb for MySQL database connection
try:
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except Exception:
    pass

# 4. Set Django Settings Module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chomotkar.settings')

# 5. Initialize Django Application with friendly error fallback
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    import traceback
    error_msg = traceback.format_exc()
    
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f"""
        <div style="font-family: Arial, sans-serif; padding: 30px; background: #fff5f5; color: #9b2c2c; border: 1px solid #feb2b2; border-radius: 8px; margin: 20px;">
            <h2 style="margin-top:0;">Chamatkar - Django Startup Diagnostics</h2>
            <pre style="background: #1a202c; color: #fed7d7; padding: 15px; border-radius: 6px; font-size: 13px; overflow: auto;">{error_msg}</pre>
        </div>
        """.encode('utf-8')
        response_headers = [('Content-type', 'text/html; charset=utf-8'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]
