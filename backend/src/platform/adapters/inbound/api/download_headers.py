"""
Response headers for routes that serve stored bytes from the API origin.

- `X-Content-Type-Options: nosniff`, so the browser never guesses a
  friendlier type than the one declared.
- A safe `Content-Disposition` with both filename forms.
- `inline` is honoured only for the types content_types lists as safe to
  render (raster images, PDF); anything else is always an attachment,
  because HTML or SVG served inline from the API origin would run script.
- `Cache-Control: private` with revalidation, and the content hash as the
  ETag, so a browser re-downloads a file only when it changed.
"""

from fastapi import Response

from src.platform.domain.services.content_types import content_disposition
from src.platform.domain.services.content_types import is_inline_safe


def build_download_headers(
    file_name: str, *, content_type: str, etag: str, disposition: str = "attachment"
) -> dict[str, str]:
    inline = disposition == "inline" and is_inline_safe(content_type)
    return {
        "Content-Disposition": content_disposition(file_name, inline=inline),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=3600, must-revalidate",
        "ETag": etag,
    }


def file_download_response(
    data: bytes, file_name: str, *, content_type: str, etag: str, disposition: str = "attachment"
) -> Response:
    headers = build_download_headers(
        file_name, content_type=content_type, etag=etag, disposition=disposition
    )
    return Response(content=data, media_type=content_type, headers=headers)


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """Whether an If-None-Match header names this ETag (or `*`)."""
    if not if_none_match:
        return False
    candidates = {c.strip().removeprefix("W/") for c in if_none_match.split(",")}
    return "*" in candidates or etag in candidates
