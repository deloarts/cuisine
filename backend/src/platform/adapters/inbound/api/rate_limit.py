"""
The rate limit of the anonymous surfaces: a router dependency that counts
each request per client address and answers 429 with `Retry-After` once an
address goes above `ANONYMOUS_REQUEST_LIMIT` requests in
`ANONYMOUS_REQUEST_WINDOW_SECONDS`. The address is the one the server
resolved from X-Forwarded-For for trusted proxies only, so a client cannot
pick its own bucket.
"""

from fastapi import Depends
from fastapi import Request

from src.platform import const
from src.platform.adapters.inbound.api.deps import get_request_rate_limiter
from src.platform.domain.exceptions import RateLimitedError
from src.platform.ports.outbound.request_rate_limiter import IRequestRateLimiter


async def limit_anonymous_requests(
    request: Request, limiter: IRequestRateLimiter = Depends(get_request_rate_limiter)
) -> None:
    address = request.client.host if request.client else "unknown"
    # Read at call time, so the limit is one constant to change.
    wait = await limiter.hit(
        f"anonymous:{address}",
        limit=const.ANONYMOUS_REQUEST_LIMIT,
        window_seconds=const.ANONYMOUS_REQUEST_WINDOW_SECONDS,
    )
    if wait:
        raise RateLimitedError("Too many requests. Try again later.", retry_after_seconds=wait)


async def limit_peering_requests(
    request: Request, limiter: IRequestRateLimiter = Depends(get_request_rate_limiter)
) -> None:
    """The same count for the peering surface, in a bucket of its own, so
    a busy peer and anonymous visitors never share a limit."""
    address = request.client.host if request.client else "unknown"
    wait = await limiter.hit(
        f"peering:{address}",
        limit=const.PEERING_REQUEST_LIMIT,
        window_seconds=const.PEERING_REQUEST_WINDOW_SECONDS,
    )
    if wait:
        raise RateLimitedError("Too many requests. Try again later.", retry_after_seconds=wait)


async def limit_oauth_requests(
    request: Request, limiter: IRequestRateLimiter = Depends(get_request_rate_limiter)
) -> None:
    """The token and revoke endpoints of the OAuth surface."""
    address = request.client.host if request.client else "unknown"
    wait = await limiter.hit(
        f"oauth:{address}",
        limit=const.OAUTH_REQUEST_LIMIT,
        window_seconds=const.OAUTH_REQUEST_WINDOW_SECONDS,
    )
    if wait:
        raise RateLimitedError("Too many requests. Try again later.", retry_after_seconds=wait)


async def limit_oauth_registrations(
    request: Request, limiter: IRequestRateLimiter = Depends(get_request_rate_limiter)
) -> None:
    """The open client registration, in a tighter bucket of its own, so
    nobody fills the client table from one address."""
    address = request.client.host if request.client else "unknown"
    wait = await limiter.hit(
        f"oauth-register:{address}",
        limit=const.OAUTH_REGISTRATION_LIMIT,
        window_seconds=const.OAUTH_REGISTRATION_WINDOW_SECONDS,
    )
    if wait:
        raise RateLimitedError("Too many registrations. Try again later.", retry_after_seconds=wait)
