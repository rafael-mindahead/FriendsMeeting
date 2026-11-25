import io
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.dependencies.current_user import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/media", tags=["Media"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

@router.post("/images", status_code=201)
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(401)
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "A imagem deve ter no máximo 5 MB.")
    try:
        source = Image.open(io.BytesIO(content))
        source.verify()
        image = Image.open(io.BytesIO(content))
        image_format = image.format
        if image_format not in ALLOWED:
            raise HTTPException(415, "Formato não suportado. Use JPEG, PNG ou WebP.")
        if image.width * image.height > 20_000_000:
            raise HTTPException(413, "Imagem com resolução muito alta.")
        image.thumbnail((1920, 1920))
        if image_format == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        filename = f"{uuid.uuid4()}{ALLOWED[image_format]}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        image.save(UPLOAD_DIR / filename)
    except HTTPException:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise HTTPException(400, "Arquivo de imagem inválido.")
    return {"url": f"/media/{filename}"}
