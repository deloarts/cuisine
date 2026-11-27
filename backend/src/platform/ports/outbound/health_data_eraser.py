"""
What happens to a user's health data when they withdraw the health data
consent: their allergies, intolerances and diets are deleted, in the same
transaction as the withdrawal. Platform owns the consent; the cookbook owns
the restrictions and registers the implementation from the composition
root (src/bootstrap). Without one registered, withdrawing is refused, so a
consent is never withdrawn while the data stays.
"""

from typing import Protocol


class IHealthDataEraser(Protocol):
    async def erase(self, user_id: int) -> int:
        """Deletes the user's health data and returns how many records went."""
        ...
