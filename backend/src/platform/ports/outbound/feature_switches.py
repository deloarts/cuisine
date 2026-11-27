"""Whether a whole feature is switched on, for any package to check. The
settings repository implements it; the cookbook checks households and
dinner guests through it."""

from typing import Protocol

from src.platform.domain.entities.settings import FeatureSettings


class IFeatureSwitches(Protocol):
    async def get_features(self) -> FeatureSettings: ...
