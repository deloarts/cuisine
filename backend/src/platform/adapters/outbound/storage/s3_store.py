"""
The `seaweedfs` provider: content as objects in one bucket of an S3 API, the
bundled SeaweedFS by default, at `files/<public id>/<variant>`.

Writes and reads go from the backend to STORAGE__ENDPOINT_URL over the
internal network. Browsers load content through presigned URLs signed for
STORAGE__PUBLIC_ENDPOINT_URL, the deployment's own address, whose nginx
forwards `/objects/` to SeaweedFS and accepts only GET and HEAD there. A
presigned URL repeats the stored type and the download header rules: only
raster images and PDF open inline, everything else downloads.

boto3 is imported when the store is built, so the app starts without it
being loaded when another provider is active. Its calls are blocking and
run in a worker thread.
"""

from typing import TYPE_CHECKING
from typing import Any

from anyio import to_thread

from src.platform.domain.services.content_types import content_disposition
from src.platform.domain.services.content_types import is_inline_safe
from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import ContentUrl

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class S3ContentStore:
    provider = "seaweedfs"

    def __init__(
        self,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str | None,
        public_endpoint_url: str | None,
        region: str,
        use_ssl: bool,
        presigned_url_seconds: int = 3600,
    ) -> None:
        self._bucket = bucket
        self._expires = presigned_url_seconds
        self._client = _client(access_key, secret_key, endpoint_url, region, use_ssl)
        # Signed for the address the browser uses; a URL signed for the
        # internal endpoint would fail verification behind nginx.
        self._public = (
            _client(access_key, secret_key, public_endpoint_url, region, use_ssl)
            if public_endpoint_url
            else self._client
        )

    async def put(self, ref: ContentRef, data: bytes, content_type: str) -> None:
        await to_thread.run_sync(
            lambda: self._client.put_object(
                Bucket=self._bucket, Key=ref.key, Body=data, ContentType=content_type
            )
        )

    async def get(self, ref: ContentRef) -> bytes | None:
        def read() -> bytes | None:
            try:
                response = self._client.get_object(Bucket=self._bucket, Key=ref.key)
            except self._client.exceptions.NoSuchKey:
                return None
            body: bytes = response["Body"].read()
            return body

        return await to_thread.run_sync(read)

    async def delete(self, ref: ContentRef) -> None:
        await to_thread.run_sync(
            lambda: self._client.delete_object(Bucket=self._bucket, Key=ref.key)
        )

    async def exists(self, ref: ContentRef) -> bool:
        from botocore.exceptions import ClientError

        def head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=ref.key)
            except ClientError:
                return False
            return True

        return await to_thread.run_sync(head)

    def url_for(
        self, ref: ContentRef, *, file_name: str, content_type: str, inline: bool
    ) -> ContentUrl | None:
        show_inline = inline and is_inline_safe(content_type)
        url = self._public.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": ref.key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": content_disposition(file_name, inline=show_inline),
                "ResponseCacheControl": "private, max-age=3600",
            },
            ExpiresIn=self._expires,
        )
        return ContentUrl(url=url)

    async def check(self) -> None:
        await to_thread.run_sync(lambda: self._client.head_bucket(Bucket=self._bucket))


def _client(
    access_key: str, secret_key: str, endpoint_url: str | None, region: str, use_ssl: bool
) -> "S3Client":
    import boto3
    from botocore.config import Config

    client: Any = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
        region_name=region,
        use_ssl=use_ssl,
        # Path-style addressing, which SeaweedFS and the /objects/ proxy
        # expect: http://host/objects/<key>, not http://objects.host/<key>.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    return client  # type: ignore[no-any-return]
