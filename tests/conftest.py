"""Pytest configuration. Uses Django test settings when running tests."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ejournal.settings.test")
