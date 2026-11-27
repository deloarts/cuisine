"""
The recent warnings and errors of this backend worker, kept in memory for
the admin area's log viewer. Every message passes the redactor before it is
kept, so the configured secrets, passwords, tokens and keys never reach the
viewer. Each worker has its own buffer; the viewer shows the worker that
answered, and the full log stays on stdout.
"""

import logging
import re
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

CAPACITY = 500
REDACTED = "[redacted]"

_PATTERNS = [
    # key=value and key: value pairs whose key names a secret.
    re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization|cookie|session)"
        r"(\"?\s*[:=]\s*\"?)([^\s\",;&]+)"
    ),
    re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._~+/=-]{8,})"),
    # Credentials inside URLs, such as a database URL.
    re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^:/\s]+):([^@/\s]+)@"),
    # Cuisine's own token formats.
    re.compile(r"\b(cuisine_(?:pat|ak|ps|pi)_)[A-Za-z0-9_-]+"),
    re.compile(r"\bwhsec_[A-Za-z0-9+/=]+"),
]


@dataclass(frozen=True)
class LogEntry:
    time: datetime
    level: str
    logger: str
    message: str


class Redactor:
    def __init__(self, secrets: list[str]) -> None:
        # Long enough to be a real secret, so short values never blank out
        # ordinary words.
        self._secrets = sorted({s for s in secrets if s and len(s) >= 8}, key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        text = _PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
        text = _PATTERNS[1].sub(lambda m: f"{m.group(1)} {REDACTED}", text)
        text = _PATTERNS[2].sub(lambda m: f"{m.group(1)}:{REDACTED}@", text)
        text = _PATTERNS[3].sub(lambda m: f"{m.group(1)}{REDACTED}", text)
        return _PATTERNS[4].sub(REDACTED, text)


class RingBufferHandler(logging.Handler):
    def __init__(self, redactor: Redactor, capacity: int = CAPACITY) -> None:
        super().__init__(level=logging.WARNING)
        self._redact = redactor
        self._entries: deque[LogEntry] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            if record.exc_info:
                formatter = logging.Formatter()
                message = f"{message}\n{formatter.formatException(record.exc_info)}"
            entry = LogEntry(
                time=datetime.fromtimestamp(record.created, tz=UTC),
                level=record.levelname,
                logger=record.name,
                message=self._redact(message)[:8000],
            )
            with self._lock:
                self._entries.append(entry)
        except Exception:  # pragma: no cover - logging must never raise
            self.handleError(record)

    def recent(self, *, min_level: int, limit: int) -> list[LogEntry]:
        with self._lock:
            entries = list(self._entries)
        kept = [e for e in entries if logging.getLevelName(e.level) >= min_level]
        return list(reversed(kept))[:limit]
