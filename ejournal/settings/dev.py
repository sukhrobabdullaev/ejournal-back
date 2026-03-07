"""
Development settings.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
# ALLOWED_HOSTS is inherited from base.py (reads from .env)

# Email backend for dev:
# - default: console (safe)
# - override: set EMAIL_BACKEND/SMTP env vars in .env to send real email (e.g. Brevo)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Optional: disable S3 in dev
USE_S3_STORAGE = False
