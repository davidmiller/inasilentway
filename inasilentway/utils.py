"""
Utilities
"""
import os
import sys

def setup_django():

    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'inasilentway.settings'

    if '.' not in sys.path:
        sys.path.append('.')

    import django
    django.setup()
