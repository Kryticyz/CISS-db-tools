"""
Image serving API routes.

Serves image files from species directories.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

# Add paths for imports
_package_dir = Path(__file__).parent.parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from config import get_settings
from api.deps import validate_species

router = APIRouter(prefix="/api/images", tags=["images"])

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

# MIME types for image formats
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


@router.get("/{species}/{filename}")
async def get_image(
    species: str = Depends(validate_species),
    filename: str = "",
) -> FileResponse:
    """
    Serve an image file.

    Args:
        species: Species directory name
        filename: Image filename

    Returns:
        FileResponse with the image

    Raises:
        HTTPException: If file not found or invalid
    """
    settings = get_settings()

    # Validate filename has image extension
    file_path = Path(filename)
    if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image extension: {file_path.suffix}",
        )

    # Construct full path
    full_path = (settings.base_dir / species / filename).resolve()

    # Security check - ensure path is within base_dir
    try:
        full_path.relative_to(settings.base_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path",
        )

    # Check file exists
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {filename}",
        )

    # Get MIME type
    mime_type = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path=full_path,
        media_type=mime_type,
        filename=filename,
    )
