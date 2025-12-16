"""
Deletion queue service for batch deletion management.

Manages an in-memory queue of files marked for deletion,
with preview and confirmation before actual deletion.
"""

import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# Add paths for imports
_package_dir = Path(__file__).parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from models.deletion import (
    DeletionPreview,
    DeletionQueue,
    DeletionReason,
    DeletionResult,
    QueuedFile,
)


class DeletionQueueService:
    """
    Thread-safe service for managing deletion queue.

    Files are added to the queue with a reason, and can be
    previewed before confirming actual deletion.
    """

    def __init__(self, base_dir: Path):
        """
        Initialize deletion queue service.

        Args:
            base_dir: Base directory for path validation
        """
        self.base_dir = base_dir.resolve()
        self._queue: dict[str, QueuedFile] = {}  # path -> QueuedFile
        self._lock = threading.Lock()

    def add_file(
        self,
        species: str,
        filename: str,
        reason: DeletionReason,
        size: int = 0,
    ) -> QueuedFile:
        """
        Add a single file to the deletion queue.

        Args:
            species: Species name
            filename: Image filename
            reason: Why the file is being deleted
            size: File size in bytes

        Returns:
            The queued file entry
        """
        path = f"{species}/{filename}"

        with self._lock:
            if path in self._queue:
                # Update reason if different
                existing = self._queue[path]
                if existing.reason != reason:
                    existing.reason = reason
                return existing

            queued = QueuedFile(
                species=species,
                filename=filename,
                path=path,
                reason=reason,
                added_at=datetime.now(),
                size=size,
            )
            self._queue[path] = queued
            return queued

    def add_files_bulk(
        self,
        files: list[dict],
        reason: DeletionReason,
    ) -> int:
        """
        Add multiple files to the queue.

        Args:
            files: List of dicts with species, filename, size keys
            reason: Reason for all files

        Returns:
            Number of files actually added (excludes duplicates)
        """
        added = 0
        with self._lock:
            for f in files:
                path = f"{f['species']}/{f['filename']}"
                if path not in self._queue:
                    self._queue[path] = QueuedFile(
                        species=f["species"],
                        filename=f["filename"],
                        path=path,
                        reason=reason,
                        added_at=datetime.now(),
                        size=f.get("size", 0),
                    )
                    added += 1
        return added

    def remove_file(self, path: str) -> bool:
        """
        Remove a file from the queue.

        Args:
            path: Relative path (species/filename)

        Returns:
            True if file was removed, False if not in queue
        """
        with self._lock:
            if path in self._queue:
                del self._queue[path]
                return True
            return False

    def clear(self) -> int:
        """
        Clear the entire queue.

        Returns:
            Number of files removed
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def get_queue(self) -> DeletionQueue:
        """
        Get current queue state.

        Returns:
            DeletionQueue with files and statistics
        """
        with self._lock:
            files = list(self._queue.values())

            by_species: dict[str, int] = {}
            by_reason: dict[str, int] = {}
            total_size = 0

            for f in files:
                by_species[f.species] = by_species.get(f.species, 0) + 1
                by_reason[f.reason.value] = by_reason.get(f.reason.value, 0) + 1
                total_size += f.size

            return DeletionQueue(
                files=files,
                total_count=len(files),
                total_size=total_size,
                total_size_human=self._format_size(total_size),
                by_species=by_species,
                by_reason=by_reason,
            )

    def get_preview(self) -> DeletionPreview:
        """
        Get preview of pending deletions.

        Returns:
            DeletionPreview with summary and warnings
        """
        queue = self.get_queue()

        # Generate warnings
        warnings = []

        # Check if any species will have all images deleted
        # (would need to check actual image counts - simplified for now)
        for species, count in queue.by_species.items():
            if count > 50:  # Arbitrary threshold for warning
                warnings.append(
                    f"Large deletion: {count} images from {species}"
                )

        return DeletionPreview(
            total_files=queue.total_count,
            total_size_bytes=queue.total_size,
            total_size_human=queue.total_size_human,
            species_affected=list(queue.by_species.keys()),
            by_reason=queue.by_reason,
            warnings=warnings,
        )

    def confirm_deletion(
        self,
        invalidate_cache_callback: Optional[Callable[[str], None]] = None,
    ) -> DeletionResult:
        """
        Execute all queued deletions.

        Args:
            invalidate_cache_callback: Called with species name after deletion

        Returns:
            DeletionResult with success/failure details
        """
        with self._lock:
            deleted: list[str] = []
            failed: list[dict] = []
            affected_species: set[str] = set()

            for path, queued_file in list(self._queue.items()):
                full_path = (self.base_dir / path).resolve()

                # Security check - ensure path is within base_dir
                try:
                    full_path.relative_to(self.base_dir)
                except ValueError:
                    failed.append({"path": path, "error": "Invalid path"})
                    continue

                try:
                    if full_path.exists():
                        full_path.unlink()
                        deleted.append(path)
                        affected_species.add(queued_file.species)
                    else:
                        failed.append({"path": path, "error": "File not found"})

                    # Remove from queue regardless
                    del self._queue[path]

                except PermissionError:
                    failed.append({"path": path, "error": "Permission denied"})
                except Exception as e:
                    failed.append({"path": path, "error": str(e)})

            # Invalidate caches for affected species
            if invalidate_cache_callback:
                for species in affected_species:
                    try:
                        invalidate_cache_callback(species)
                    except Exception:
                        pass  # Don't fail deletion due to cache issues

            return DeletionResult(
                success=len(failed) == 0,
                deleted_count=len(deleted),
                deleted_files=deleted,
                failed_count=len(failed),
                failed_files=failed,
                affected_species=list(affected_species),
            )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
