#!/usr/bin/env python
import os
import sys
from ecomm.ngrok import start_ngrok

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecomm.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Khởi động ngrok trước khi chạy server
    if sys.argv[1] == 'runserver':
        start_ngrok()
    
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main() 