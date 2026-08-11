"""Generate browser-safe preview copies while preserving source media."""

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


class TiffPreviewConverter:
    """Create a bounded PNG preview for TIFF images extracted from DOCX."""

    TIFF_EXTENSIONS = {".tif", ".tiff"}
    MAX_DIMENSION = 2400

    def create(self, source: Path) -> Path | None:
        if source.suffix.lower() not in self.TIFF_EXTENSIONS:
            return None

        preview = source.with_name(f"{source.stem}_preview.png")
        try:
            # Decode from memory. Some Windows libtiff builds can fail on an
            # otherwise valid compressed TIFF when it is opened by file path.
            with Image.open(BytesIO(source.read_bytes())) as image:
                # A TIFF can have several pages; the first page is the document preview.
                image.seek(0)
                image.load()
                converted = self._to_browser_image(image)
                converted.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), Image.Resampling.LANCZOS)
                converted.save(preview, format="PNG", optimize=True)
            return preview
        except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError):
            preview.unlink(missing_ok=True)
            return None

    @staticmethod
    def _to_browser_image(image: Image.Image) -> Image.Image:
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            return image.convert("RGBA")
        return image.convert("RGB")
