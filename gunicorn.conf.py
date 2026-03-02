"""Gunicorn config for production."""
import os

workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

# Avoid /dev/shm in Docker (can cause OOM on small instances)
worker_tmp_dir = "/tmp"

# Handle "no URI read" gracefully (health checks, connection drops)
def on_starting(server):
    pass

def when_ready(server):
    pass
