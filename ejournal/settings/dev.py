"""
Development settings.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "127.0.0.1:8000"]

# Email backend for dev:
# - default: console (safe)
# - override: set EMAIL_BACKEND/SMTP env vars in .env to send real email (e.g. Brevo)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Optional: disable S3 in dev
USE_S3_STORAGE = False
