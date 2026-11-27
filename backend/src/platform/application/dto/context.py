"""Where a request came from, carried into the use cases that write the
security log."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    client_ip: str | None = None
    user_agent: str | None = None
