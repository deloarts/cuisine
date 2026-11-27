"""
IImageProcessor with Pillow.

Every image is decoded and encoded again, so nothing of the uploaded file
survives except its pixels: EXIF, GPS, ICC comments and any payload hidden
after the image data are dropped. The orientation stored in EXIF is applied
to the pixels first, so a photo taken upright stays upright. Animated GIFs
keep their first frame only. The pixel count is read from the header and
checked before any pixel is decoded, which guards against decompression
bombs.
"""

from io import BytesIO

from anyio import to_thread
from PIL import Image
from PIL import ImageOps
from PIL import UnidentifiedImageError

from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.ports.outbound.image_processor import ProcessedImage

# About 64 megapixels, far above any phone camera and far below a bomb.
MAX_PIXELS = 64_000_000
WEBP_QUALITY = 82
THUMBNAIL_QUALITY = 75


class PillowImageProcessor:
    def __init__(self, max_edge: int, thumbnail_edge: int) -> None:
        self._max_edge = max_edge
        self._thumbnail_edge = thumbnail_edge

    async def process(self, data: bytes) -> ProcessedImage:
        """Runs the re-encoding in a worker thread."""
        return await to_thread.run_sync(self.process_sync, data)

    def process_sync(self, data: bytes) -> ProcessedImage:
        # Pillow only warns between one and two times its own limit, so the
        # limit is enforced here from the header size, before decoding.
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        try:
            with Image.open(BytesIO(data)) as source:
                width, height = source.size
                if width * height > MAX_PIXELS:
                    raise FileTypeNotAcceptedError("The image has too many pixels.")
                source.seek(0)
                image = ImageOps.exif_transpose(source)
                image = self._normalise_mode(image)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
            raise FileTypeNotAcceptedError("The file is not a readable image.") from exc

        image.thumbnail((self._max_edge, self._max_edge), Image.Resampling.LANCZOS)
        full = self._encode(image, WEBP_QUALITY)
        thumb_image = image.copy()
        thumb_image.thumbnail(
            (self._thumbnail_edge, self._thumbnail_edge), Image.Resampling.LANCZOS
        )
        thumbnail = self._encode(thumb_image, THUMBNAIL_QUALITY)
        return ProcessedImage(
            data=full, width=image.width, height=image.height, thumbnail=thumbnail
        )

    @staticmethod
    def _normalise_mode(image: Image.Image) -> Image.Image:
        """RGB or RGBA, the modes WebP stores; palette images with
        transparency keep it."""
        if image.mode in ("RGB", "RGBA"):
            result = image.copy()
        else:
            has_alpha = image.mode in ("LA", "PA") or (
                image.mode == "P" and "transparency" in image.info
            )
            result = image.convert("RGBA" if has_alpha else "RGB")
        # Drops the source's EXIF, XMP and ICC data, which Pillow would
        # otherwise carry over into the WebP.
        result.info.clear()
        return result

    @staticmethod
    def _encode(image: Image.Image, quality: int) -> bytes:
        out = BytesIO()
        # The info dict was cleared and WebP gets no exif, xmp or icc
        # argument, so no metadata is written.
        image.save(out, format="WEBP", quality=quality, method=4)
        return out.getvalue()
