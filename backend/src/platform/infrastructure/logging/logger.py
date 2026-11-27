"""
Single logger instance used across the codebase. cfg.log_format picks text
for humans or one JSON object per line for a log aggregator.
"""

import json
import logging

from src.platform.infrastructure.config.settings import cfg
from src.platform.infrastructure.logging.ring_buffer import Redactor
from src.platform.infrastructure.logging.ring_buffer import RingBufferHandler


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


log = logging.getLogger("cuisine")
log.setLevel(logging.DEBUG)

if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(cfg.log_level)
    if cfg.log_format == "json":
        _handler.setFormatter(JsonFormatter())
    else:
        _handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
    log.addHandler(_handler)
    log.propagate = False  # don't double-print via uvicorn's root handler


def _configured_secrets() -> list[str]:
    values = [
        cfg.security.secret_key,
        cfg.security.encryption_key,
        cfg.security.encryption_key_previous or "",
        cfg.init.password,
        cfg.storage.secret_key or "",
    ]
    # The password inside the database URL.
    if "://" in cfg.database.url and "@" in cfg.database.url:
        credentials = cfg.database.url.split("://", 1)[1].split("@", 1)[0]
        values.append(credentials.split(":", 1)[-1])
    return values


# Warnings and errors for the admin area's log viewer, from the app and
# from uvicorn and SQLAlchemy, which log through the root logger.
recent_logs = RingBufferHandler(Redactor(_configured_secrets()))
log.addHandler(recent_logs)
logging.getLogger().addHandler(recent_logs)
