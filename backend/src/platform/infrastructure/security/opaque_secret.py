"""
Opaque bearer secrets for personal access tokens, API keys and the
trusted-device cookie. Deliberately not JWTs and not bcrypt: a long-lived,
high-entropy secret wants O(1) lookup by hash and instant revocation, and
bcrypt's random salt makes lookup by hash impossible. SHA-256 over a
cryptographically random token is the standard approach (the same shape
GitHub and Stripe keys use).
"""

import hashlib
import secrets

# Characters after the prefix kept for display, so a user can recognise a
# token without ever seeing the whole value again.
_DISPLAY_LEN = 8


class Sha256SecretHasher:
    def generate(self, prefix: str) -> str:
        return prefix + secrets.token_urlsafe(32)

    def hash(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def display_prefix(self, secret: str, prefix: str) -> str:
        """The prefix plus a few characters, enough to tell tokens apart.
        The random part may itself contain underscores, so the prefix is
        passed in rather than searched for."""
        return secret[: len(prefix) + _DISPLAY_LEN]
