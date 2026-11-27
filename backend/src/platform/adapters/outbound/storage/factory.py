"""
Builds the content store for a provider. The database provider lives on the
request's session; the local and S3 stores hold no per-request state and
are built once per process and provider.
"""

from functools import cache

from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.storage.local_store import LocalContentStore
from src.platform.adapters.outbound.storage.postgres_store import PostgresContentStore
from src.platform.adapters.outbound.storage.s3_store import S3ContentStore
from src.platform.infrastructure.config.settings import cfg
from src.platform.ports.outbound.file_content_store import IFileContentStore

PROVIDERS = ("postgres", "local", "seaweedfs")


class StorageConfigurationError(RuntimeError):
    """The provider's settings are incomplete."""


def content_store(provider: str, session: AsyncSession) -> IFileContentStore:
    """The store for `provider`, which defaults to STORAGE__PROVIDER."""
    match provider:
        case "postgres":
            return PostgresContentStore(session)
        case "local":
            return _local(cfg.local_storage.base_dir)
        case "seaweedfs":
            return _s3()
        case _:
            raise StorageConfigurationError(f"Unknown storage provider {provider!r}.")


def active_content_store(session: AsyncSession) -> IFileContentStore:
    return content_store(cfg.storage.provider, session)


@cache
def _local(base_dir: str) -> LocalContentStore:
    return LocalContentStore(base_dir)


@cache
def _s3() -> S3ContentStore:
    s = cfg.storage
    if not s.access_key or not s.secret_key:
        raise StorageConfigurationError(
            "STORAGE__ACCESS_KEY and STORAGE__SECRET_KEY are required for the seaweedfs provider."
        )
    if not s.endpoint_url:
        raise StorageConfigurationError(
            "STORAGE__ENDPOINT_URL is required for the seaweedfs provider."
        )
    return S3ContentStore(
        bucket=s.bucket_name,
        access_key=s.access_key,
        secret_key=s.secret_key,
        endpoint_url=s.endpoint_url,
        public_endpoint_url=s.public_endpoint_url,
        region=s.region,
        use_ssl=s.use_ssl,
        presigned_url_seconds=s.presigned_url_seconds,
    )
