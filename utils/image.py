"""Image and media upload utilities."""

from __future__ import annotations
import io
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image

from config.settings import settings

# MIME types treated as video
VIDEO_MIME_TYPES = {
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    "video/x-msvideo", "video/x-matroska",
}

VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}


async def save_uploaded_file(
    file_data: bytes,
    filename: str,
    mime_type: str,
    subfolder: str = "media",
) -> str:
    """
    Save any uploaded file. Images are converted to WebP; videos are stored as-is.
    Returns relative URL path.
    """
    ext = Path(filename).suffix.lower()
    if mime_type in VIDEO_MIME_TYPES or ext in VIDEO_EXTENSIONS:
        # Keep original extension for video files
        safe_ext = ext if ext in VIDEO_EXTENSIONS else ".mp4"
        out_filename = f"{uuid.uuid4().hex}{safe_ext}"
        save_dir = settings.UPLOAD_DIR / subfolder
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / out_filename).write_bytes(file_data)
        return f"/static/uploads/{subfolder}/{out_filename}"
    # Default: compress and convert to WebP
    return await save_uploaded_image(file_data, subfolder=subfolder)


async def save_uploaded_image(
    file_data: bytes,
    subfolder: str = "products",
    max_width: int = 1200,
    quality: int = 85,
) -> str:
    """
    Save uploaded image as WebP, resizing if needed.
    Returns relative URL path.
    """
    img = Image.open(io.BytesIO(file_data))

    # Convert to RGB (handles PNG transparency → white bg)
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if wider than max_width
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # Save as WebP
    filename = f"{uuid.uuid4().hex}.webp"
    save_dir = settings.UPLOAD_DIR / subfolder
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    img.save(save_path, "WEBP", quality=quality, optimize=True)

    return f"/static/uploads/{subfolder}/{filename}"
