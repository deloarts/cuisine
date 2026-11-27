"""Every ORM model of every package on one metadata. Alembic, the test
schema and the composition root import Base from here, so Platform's models
package never has to name the cookbook."""

import src.cookbook.adapters.outbound.persistence.models  # noqa: F401
from src.platform.adapters.outbound.persistence.models import Base

__all__ = ["Base"]
