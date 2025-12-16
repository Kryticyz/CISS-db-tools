"""
Deletion queue API routes.

Manages the deletion queue for batch file deletion.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Add paths for imports
_package_dir = Path(__file__).parent.parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from models.deletion import (
    DeletionPreview,
    DeletionQueue,
    DeletionResult,
    QueueAddRequest,
    QueuedFile,
)
from api.deps import get_deletion_queue, get_detection_service
from services.deletion_queue import DeletionQueueService
from services.detection_service import DetectionService

router = APIRouter(prefix="/api/deletion", tags=["deletion"])


@router.get("/queue", response_model=DeletionQueue)
async def get_queue(
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
) -> DeletionQueue:
    """
    Get current deletion queue.

    Returns the list of files queued for deletion with statistics.
    """
    return deletion_queue.get_queue()


@router.post("/queue", response_model=dict)
async def add_to_queue(
    request: QueueAddRequest,
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
) -> dict:
    """
    Add files to deletion queue.

    Args:
        request: Files to add with reason

    Returns:
        Count of files added
    """
    added = deletion_queue.add_files_bulk(request.files, request.reason)
    return {"added": added, "total": deletion_queue.get_queue().total_count}


@router.delete("/queue/{species}/{filename}")
async def remove_from_queue(
    species: str,
    filename: str,
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
) -> dict:
    """
    Remove a file from the queue.

    Args:
        species: Species name
        filename: Image filename

    Returns:
        Success status
    """
    path = f"{species}/{filename}"
    removed = deletion_queue.remove_file(path)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not in queue: {path}",
        )

    return {"removed": True, "path": path}


@router.post("/queue/clear")
async def clear_queue(
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
) -> dict:
    """
    Clear the entire deletion queue.

    Returns:
        Count of files removed
    """
    count = deletion_queue.clear()
    return {"cleared": count}


@router.get("/preview", response_model=DeletionPreview)
async def get_preview(
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
) -> DeletionPreview:
    """
    Get preview of pending deletions.

    Returns summary with warnings before confirmation.
    """
    return deletion_queue.get_preview()


@router.post("/confirm", response_model=DeletionResult)
async def confirm_deletion(
    deletion_queue: DeletionQueueService = Depends(get_deletion_queue),
    detection_service: DetectionService = Depends(get_detection_service),
) -> DeletionResult:
    """
    Confirm and execute all queued deletions.

    This permanently deletes the files from disk.

    Returns:
        DeletionResult with success/failure details
    """
    # Define callback to invalidate cache after deletion
    def invalidate_callback(species: str) -> None:
        detection_service.invalidate_cache(species)

    return deletion_queue.confirm_deletion(invalidate_callback)
