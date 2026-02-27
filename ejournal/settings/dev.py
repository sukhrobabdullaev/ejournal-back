"""
Development settings.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "127.0.0.1:8000"]

# Use console email backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Optional: disable S3 in dev
USE_S3_STORAGE = False
