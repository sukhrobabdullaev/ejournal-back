"""
WSGI config for ejournal project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ejournal.settings.dev")
application = get_wsgi_application()
