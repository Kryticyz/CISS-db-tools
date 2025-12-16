"""
Common image-related utilities.
"""

from pathlib import Path
from typing import List

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def get_image_files(directory: Path) -> List[Path]:
    """
    Get all image files in a directory.

    Args:
        directory: Path to the directory

    Returns:
        List of image file paths, sorted alphabetically
    """
    image_files = []

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            image_files.append(file_path)

    return sorted(image_files)
