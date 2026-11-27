"""Re-encodes an uploaded image so nothing of the original file survives:
metadata such as EXIF and GPS is dropped, and the result is a WebP with a
thumbnail."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int
    thumbnail: bytes


class IImageProcessor(Protocol):
    async def process(self, data: bytes) -> ProcessedImage:
        """Raises FileTypeNotAcceptedError when the bytes are not an image.
        Async because decoding and encoding are slow CPU work that must not
        stall the event loop."""
        ...
