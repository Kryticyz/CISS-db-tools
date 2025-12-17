"""Deletion queue Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DeletionReason(str, Enum):
    """Reason for marking an image for deletion."""

    DUPLICATE = "duplicate"
    SIMILAR = "similar"
    OUTLIER = "outlier"
    MANUAL = "manual"


class QueuedFile(BaseModel):
    """A file queued for deletion."""

    species: str = Field(description="Species name")
    filename: str = Field(description="Image filename")
    path: str = Field(description="Relative path: species/filename")
    reason: DeletionReason = Field(description="Why the file was queued")
    added_at: datetime = Field(description="When file was added to queue")
    size: int = Field(ge=0, description="File size in bytes")
    thumbnail_path: Optional[str] = Field(
        default=None, description="Path to thumbnail if available"
    )


class QueueAddRequest(BaseModel):
    """Request to add files to deletion queue."""

    files: list[dict] = Field(description="Files to add: {species, filename, size}")
    reason: DeletionReason = Field(description="Reason for deletion")


class DeletionQueue(BaseModel):
    """Current deletion queue state."""

    files: list[QueuedFile] = Field(description="Files in queue")
    total_count: int = Field(ge=0, description="Total files in queue")
    total_size: int = Field(ge=0, description="Total size of queued files")
    total_size_human: str = Field(description="Human-readable size")
    by_species: dict[str, int] = Field(description="File count per species")
    by_reason: dict[str, int] = Field(description="File count per reason")


class DeletionPreview(BaseModel):
    """Preview of pending deletions before confirmation."""

    total_files: int = Field(ge=0, description="Total files to delete")
    total_size_bytes: int = Field(ge=0, description="Total size in bytes")
    total_size_human: str = Field(description="Human-readable size")
    species_affected: list[str] = Field(description="Species that will be affected")
    by_reason: dict[str, int] = Field(description="Breakdown by reason")
    warnings: list[str] = Field(description="Warnings about the deletion")


class DeletionResult(BaseModel):
    """Result after deletion is executed."""

    success: bool = Field(description="Whether all deletions succeeded")
    deleted_count: int = Field(ge=0, description="Number of files deleted")
    deleted_files: list[str] = Field(description="Paths of deleted files")
    failed_count: int = Field(ge=0, description="Number of failed deletions")
    failed_files: list[dict] = Field(description="Files that failed with errors")
    affected_species: list[str] = Field(description="Species that were affected")
