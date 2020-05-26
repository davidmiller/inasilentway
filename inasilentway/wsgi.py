"""
WSGI config for inasilentway project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inasilentway.settings")


try:
    # Serve static files on Heroku
    from dj_static import Cling
    application = Cling(get_wsgi_application())
except ImportError:
    application = get_wsgi_application()
