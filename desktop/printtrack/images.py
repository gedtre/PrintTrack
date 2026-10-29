"""Decode uploaded images independently of Qt image plugins and strip metadata."""
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from .store import ValidationError


def photo_png(path):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.format not in ['PNG', 'JPEG', 'WEBP', 'BMP', 'GIF', 'TIFF', 'ICO', 'AVIF']:
                    raise ValidationError('Pasirinkite PNG, JPG, WebP, BMP, GIF, TIFF arba ICO nuotrauką.')
                if source.width * source.height > 40_000_000:
                    raise ValidationError('Nuotrauka per didelė. Sumažinkite ją iki 40 milijonų taškų.')
                image = ImageOps.exif_transpose(source).convert('RGBA')
                image.thumbnail((640, 640), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                # Do not propagate embedded profiles or arbitrary source metadata.
                clean = Image.frombytes('RGBA', image.size, image.tobytes())
                clean.save(output, format='PNG')
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, MemoryError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValidationError('Nepavyko perskaityti nuotraukos. Pasirinkite kitą PNG, JPG / JPEG arba WebP failą. Ankstesnė nuotrauka nepakeista.') from error
