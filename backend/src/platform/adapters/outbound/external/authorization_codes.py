"""IAuthorizationCodeStore on Redis, and an in-process one for tests."""

import json
import time

from redis.asyncio import Redis

from src.platform.domain.entities.oauth import AuthorizationCode

_PREFIX = "cuisine:oauth:code"
_REDEEMED = "cuisine:oauth:redeemed"


def _dump(code: AuthorizationCode) -> str:
    return json.dumps(
        {
            "client_id": code.client_id,
            "user_id": code.user_id,
            "redirect_uri": code.redirect_uri,
            "code_challenge": code.code_challenge,
            "permissions": list(code.permissions),
            "token_version": code.token_version,
        }
    )


def _load(raw: str | bytes) -> AuthorizationCode:
    data = json.loads(raw)
    return AuthorizationCode(
        client_id=int(data["client_id"]),
        user_id=int(data["user_id"]),
        redirect_uri=str(data["redirect_uri"]),
        code_challenge=str(data["code_challenge"]),
        permissions=tuple(str(p) for p in data["permissions"]),
        token_version=int(data["token_version"]),
    )


class RedisAuthorizationCodeStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def put(self, code_hash: str, code: AuthorizationCode, ttl_seconds: int) -> None:
        await self._redis.set(f"{_PREFIX}:{code_hash}", _dump(code), ex=ttl_seconds)

    async def take(self, code_hash: str) -> AuthorizationCode | None:
        raw = await self._redis.getdel(f"{_PREFIX}:{code_hash}")
        return _load(raw) if raw else None

    async def mark_redeemed(self, code_hash: str, grant_id: int, ttl_seconds: int) -> None:
        await self._redis.set(f"{_REDEEMED}:{code_hash}", str(grant_id), ex=ttl_seconds)

    async def redeemed_grant(self, code_hash: str) -> int | None:
        raw = await self._redis.get(f"{_REDEEMED}:{code_hash}")
        return int(raw) if raw else None


class InMemoryAuthorizationCodeStore:
    def __init__(self) -> None:
        self._codes: dict[str, tuple[float, AuthorizationCode]] = {}
        self._redeemed: dict[str, tuple[float, int]] = {}

    async def put(self, code_hash: str, code: AuthorizationCode, ttl_seconds: int) -> None:
        self._codes[code_hash] = (time.monotonic() + ttl_seconds, code)

    async def take(self, code_hash: str) -> AuthorizationCode | None:
        entry = self._codes.pop(code_hash, None)
        if entry is None or entry[0] <= time.monotonic():
            return None
        return entry[1]

    async def mark_redeemed(self, code_hash: str, grant_id: int, ttl_seconds: int) -> None:
        self._redeemed[code_hash] = (time.monotonic() + ttl_seconds, grant_id)

    async def redeemed_grant(self, code_hash: str) -> int | None:
        entry = self._redeemed.get(code_hash)
        if entry is None or entry[0] <= time.monotonic():
            return None
        return entry[1]
