"""The hourly send limit, counted per backend worker in memory. Cuisine
sends few mails (tests and operational alerts), so a limit per process
bounds a runaway alert loop without another moving part."""

import time
from collections import deque


class InMemorySendLimiter:
    def __init__(self) -> None:
        self._sent: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        window = self._sent.setdefault(key, deque())
        while window and now - window[0] > 3600:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True
