"""Ejournal project package."""

from ejournal.celery import app as celery_app

__all__ = ("celery_app",)
