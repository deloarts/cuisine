"""Generates opaque bearer secrets and hashes them for lookup. Used for
personal access tokens, API keys and trusted-device cookies."""

from typing import Protocol


class ISecretHasher(Protocol):
    def generate(self, prefix: str) -> str: ...
    def hash(self, secret: str) -> str: ...
    def display_prefix(self, secret: str, prefix: str) -> str: ...
