"""Public display of avatar images, authenticated owner-only modifications."""
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.Database.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.models.user_avatar import UserAvatar

router = APIRouter(prefix="/api/v1/users", tags=["Profile photos"])
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000

def sanitize_image(raw: bytes) -> bytes:
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "A foto deve ter no maximo 2 MB")
    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in ("PNG", "JPEG", "WEBP"):
                raise HTTPException(422, "Use PNG, JPEG ou WebP")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise HTTPException(413, "Resolucao da imagem muito alta")
            # Render from pixels only; EXIF, GPS and other metadata are discarded.
            image = ImageOps.fit(
                ImageOps.exif_transpose(source).convert("RGB"), (320, 320),
                method=Image.Resampling.LANCZOS,
            )
            out = BytesIO()
            image.save(out, format="WEBP", quality=82, method=6)
            return out.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Arquivo de imagem invalido") from exc

@router.put("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Limit reading even when Content-Length is forged or missing.
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    image = sanitize_image(raw)
    revision = uuid4()
    avatar = db.get(UserAvatar, user.id)
    if avatar is None:
        avatar = UserAvatar(user_id=user.id, image=image, media_type="image/webp", revision=revision)
        db.add(avatar)
    else:
        avatar.image = image
        avatar.media_type = "image/webp"
        avatar.revision = revision
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, "Nao foi possivel salvar a foto") from exc
    return {"avatar_url": f"/api/v1/users/{user.id}/avatar?v={revision}", "revision": str(revision)}

@router.get("/{user_id}/avatar")
def get_avatar(user_id: UUID, db: Session = Depends(get_db)):
    avatar = db.get(UserAvatar, user_id)
    if avatar is None:
        raise HTTPException(404, "Foto nao encontrada")
    return Response(
        content=avatar.image, media_type="image/webp",
        headers={"Cache-Control": "public, max-age=60", "X-Content-Type-Options": "nosniff"},
    )

@router.delete("/me/avatar", status_code=204)
def delete_avatar(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    avatar = db.get(UserAvatar, user.id)
    if avatar is not None:
        db.delete(avatar)
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(503, "Nao foi possivel remover a foto") from exc
    return Response(status_code=204)
