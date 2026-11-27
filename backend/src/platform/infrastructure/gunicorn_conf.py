"""Gunicorn settings for the production image. Read by
`gunicorn -c src/platform/infrastructure/gunicorn_conf.py`."""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '3000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "src.platform.infrastructure.gunicorn_worker.CuisineUvicornWorker"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
# Only the reverse proxy in front of the backend may set X-Forwarded-For.
forwarded_allow_ips = os.getenv("NETWORK__TRUSTED_PROXIES", "127.0.0.1")
