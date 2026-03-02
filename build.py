"""
Build script for Vercel deployment.
This runs during the build phase to set up Django.
"""

import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mazale.settings')
    
    # Run Django setup
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Run migrations
    execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    
    # Collect static files
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear'])

if __name__ == '__main__':
    main()
