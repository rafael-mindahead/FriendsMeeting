from io import BytesIO

import pytest
from PIL import Image
from fastapi import HTTPException

from app.routers.avatars import MAX_UPLOAD_BYTES, sanitize_image


def test_rejects_empty_file():
    with pytest.raises(HTTPException) as error:
        sanitize_image(b"")
    assert error.value.status_code == 413


def test_rejects_oversized_file():
    with pytest.raises(HTTPException) as error:
        sanitize_image(b"x" * (MAX_UPLOAD_BYTES + 1))
    assert error.value.status_code == 413


def test_rejects_fake_png():
    with pytest.raises(HTTPException) as error:
        sanitize_image(b"not an actual png")
    assert error.value.status_code == 422


def test_removes_embedded_metadata_and_resizes():
    image = Image.new("RGB", (800, 500), "red")
    exif = Image.Exif()
    exif[270] = "Private camera metadata"
    out = BytesIO()
    image.save(out, format="JPEG", exif=exif)
    sanitized = sanitize_image(out.getvalue())
    with Image.open(BytesIO(sanitized)) as result:
        assert result.format == "WEBP"
        assert result.size == (320, 320)
        assert "exif" not in result.info


def test_rejects_unsupported_gif():
    out = BytesIO()
    Image.new("RGB", (20, 20), "blue").save(out, format="GIF")
    with pytest.raises(HTTPException) as error:
        sanitize_image(out.getvalue())
    assert error.value.status_code == 422
