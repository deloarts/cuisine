"""
Password hashing. Thin wrapper around bcrypt.

bcrypt is deliberately slow CPU work (about 100 ms per hash), so the async
methods run it in a worker thread instead of stalling the event loop.

bcrypt only ever reads the first 72 bytes of its input, and bcrypt 5 raises
on anything longer, so this module cuts the UTF-8 bytes at 72 itself.
"""

from anyio import to_thread
from bcrypt import checkpw
from bcrypt import gensalt
from bcrypt import hashpw

BCRYPT_MAX_INPUT_BYTES = 72


def _bcrypt_input(value: str) -> bytes:
    return value.encode("utf-8")[:BCRYPT_MAX_INPUT_BYTES]


def verify_hash(plain: str, hashed: str) -> bool:
    try:
        return checkpw(_bcrypt_input(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def get_hash(value: str) -> str:
    return hashpw(_bcrypt_input(value), gensalt()).decode("utf-8")


class BcryptPasswordHasher:
    async def hash(self, plain: str) -> str:
        return await to_thread.run_sync(get_hash, plain)

    async def verify(self, plain: str, hashed: str) -> bool:
        return await to_thread.run_sync(verify_hash, plain, hashed)
