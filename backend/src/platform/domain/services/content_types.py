"""
Which file types the storage accepts, which of them a browser may render
inline, and the Content-Disposition header for a download.

Only raster images and PDFs are rendered inline. Everything else, notably
HTML and SVG, which a browser would execute if served inline from the API's
own origin, is always sent as an attachment.
"""

from urllib.parse import quote

IMAGE_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
DOCUMENT_CONTENT_TYPES: frozenset[str] = frozenset({"application/pdf"})
ACCEPTED_CONTENT_TYPES: frozenset[str] = IMAGE_CONTENT_TYPES | DOCUMENT_CONTENT_TYPES
INLINE_SAFE_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
)


def normalise_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def is_inline_safe(content_type: str) -> bool:
    return normalise_content_type(content_type) in INLINE_SAFE_CONTENT_TYPES


def safe_file_name(file_name: str) -> str:
    """The name without path parts and control characters, never empty."""
    name = file_name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch >= " " and ch != "\x7f").strip()
    return name[:255] or "file"


def content_disposition(file_name: str, *, inline: bool) -> str:
    """Both the plain `filename=` and the RFC 5987 `filename*=` forms, so
    non-ASCII names survive, with quotes and CRLF removed from the plain one."""
    name = safe_file_name(file_name)
    ascii_name = name.encode("ascii", "replace").decode("ascii").replace('"', "")
    kind = "inline" if inline else "attachment"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name, safe='')}"
