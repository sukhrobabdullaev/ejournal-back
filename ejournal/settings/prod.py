"""
Production settings (on-premise).
"""
from .base import *  # noqa: F401, F403

DEBUG = False
USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)  # On-premise: local storage

# Security
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
