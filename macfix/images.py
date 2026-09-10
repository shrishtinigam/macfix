"""Validate and encode a single image; discard metadata before upload."""

import base64
import io
import warnings
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 20_000_000


class ImageError(RuntimeError):
    """An image cannot safely be loaded."""


def load_image(path: str | Path) -> str:
    try:
        with Path(path).expanduser().open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ImageError('Image exceeds 8 MB. Crop or export a smaller PNG or JPEG.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG', 'JPEG'):
                    raise ImageError('Use a PNG or JPEG image.')
                if image.width * image.height > MAX_PIXELS:
                    raise ImageError('Image exceeds 20 million pixels. Crop a smaller area.')
                image.load()
                # Normalize orientation and remove metadata; preserve readable text.
                oriented = ImageOps.exif_transpose(image).convert('RGBA')
                flattened = Image.new('RGB', oriented.size, 'white')
                flattened.paste(oriented, mask=oriented.getchannel('A'))
                output = io.BytesIO()
                flattened.save(output, format='PNG')
        encoded = output.getvalue()
        if len(encoded) > MAX_BYTES:
            raise ImageError('Prepared image exceeds 8 MB. Crop a smaller area.')
        return 'data:image/png;base64,' + base64.b64encode(encoded).decode('ascii')
    except ImageError:
        raise
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise ImageError('Cannot read this image. Choose a valid, accessible PNG or JPEG.') from None
