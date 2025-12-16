"""
Tests for service layer.
"""

from pathlib import Path

import pytest

from services.deletion_queue import DeletionQueueService
from models.deletion import DeletionReason


class TestDeletionQueueService:
    """Tests for DeletionQueueService."""

    def test_add_file(self, deletion_queue: DeletionQueueService):
        """Test adding a single file to the queue."""
        result = deletion_queue.add_file(
            species="Test_Species_A",
            filename="image_0.jpg",
            reason=DeletionReason.DUPLICATE,
            size=1000,
        )

        assert result.species == "Test_Species_A"
        assert result.filename == "image_0.jpg"
        assert result.reason == DeletionReason.DUPLICATE
        assert result.size == 1000

        queue = deletion_queue.get_queue()
        assert queue.total_count == 1

    def test_add_duplicate_file(self, deletion_queue: DeletionQueueService):
        """Test that adding the same file twice doesn't duplicate."""
        deletion_queue.add_file(
            species="Test_Species_A",
            filename="image_0.jpg",
            reason=DeletionReason.DUPLICATE,
            size=1000,
        )
        deletion_queue.add_file(
            species="Test_Species_A",
            filename="image_0.jpg",
            reason=DeletionReason.SIMILAR,  # Different reason
            size=1000,
        )

        queue = deletion_queue.get_queue()
        assert queue.total_count == 1
        # Reason should be updated to the latest
        assert queue.files[0].reason == DeletionReason.SIMILAR

    def test_add_files_bulk(self, deletion_queue: DeletionQueueService):
        """Test adding multiple files at once."""
        files = [
            {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000},
            {"species": "Test_Species_A", "filename": "image_1.jpg", "size": 2000},
            {"species": "Test_Species_B", "filename": "image_0.jpg", "size": 1500},
        ]

        added = deletion_queue.add_files_bulk(files, DeletionReason.DUPLICATE)

        assert added == 3

        queue = deletion_queue.get_queue()
        assert queue.total_count == 3
        assert queue.total_size == 4500
        assert queue.by_species["Test_Species_A"] == 2
        assert queue.by_species["Test_Species_B"] == 1

    def test_remove_file(self, deletion_queue: DeletionQueueService):
        """Test removing a file from the queue."""
        deletion_queue.add_file(
            species="Test_Species_A",
            filename="image_0.jpg",
            reason=DeletionReason.DUPLICATE,
            size=1000,
        )

        removed = deletion_queue.remove_file("Test_Species_A/image_0.jpg")
        assert removed is True

        queue = deletion_queue.get_queue()
        assert queue.total_count == 0

    def test_remove_nonexistent_file(self, deletion_queue: DeletionQueueService):
        """Test removing a file that's not in the queue."""
        removed = deletion_queue.remove_file("Test_Species_A/nonexistent.jpg")
        assert removed is False

    def test_clear_queue(self, deletion_queue: DeletionQueueService):
        """Test clearing the entire queue."""
        # Add some files
        files = [
            {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000},
            {"species": "Test_Species_A", "filename": "image_1.jpg", "size": 2000},
        ]
        deletion_queue.add_files_bulk(files, DeletionReason.DUPLICATE)

        cleared = deletion_queue.clear()
        assert cleared == 2

        queue = deletion_queue.get_queue()
        assert queue.total_count == 0

    def test_get_preview(self, deletion_queue: DeletionQueueService):
        """Test getting deletion preview."""
        files = [
            {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000},
            {"species": "Test_Species_B", "filename": "image_0.jpg", "size": 2000},
        ]
        deletion_queue.add_files_bulk(files, DeletionReason.OUTLIER)

        preview = deletion_queue.get_preview()

        assert preview.total_files == 2
        assert preview.total_size_bytes == 3000
        assert len(preview.species_affected) == 2
        assert "outlier" in preview.by_reason

    def test_confirm_deletion(
        self, deletion_queue: DeletionQueueService, temp_species_dir: Path
    ):
        """Test confirming deletion actually deletes files."""
        # Add a file that exists
        deletion_queue.add_file(
            species="Test_Species_A",
            filename="image_0.jpg",
            reason=DeletionReason.DUPLICATE,
            size=1000,
        )

        # Verify file exists
        file_path = temp_species_dir / "Test_Species_A" / "image_0.jpg"
        assert file_path.exists()

        # Confirm deletion
        result = deletion_queue.confirm_deletion()

        assert result.success is True
        assert result.deleted_count == 1
        assert "Test_Species_A/image_0.jpg" in result.deleted_files
        assert not file_path.exists()

    def test_confirm_deletion_nonexistent_file(
        self, deletion_queue: DeletionQueueService
    ):
        """Test deletion of nonexistent file reports failure."""
        deletion_queue.add_file(
            species="Test_Species_A",
            filename="nonexistent.jpg",
            reason=DeletionReason.DUPLICATE,
            size=1000,
        )

        result = deletion_queue.confirm_deletion()

        assert result.success is False
        assert result.failed_count == 1

    def test_format_size(self):
        """Test size formatting helper."""
        service = DeletionQueueService(Path("/tmp"))

        assert service._format_size(0) == "0 B"
        assert service._format_size(500) == "500.0 B"
        assert service._format_size(1024) == "1.0 KB"
        assert service._format_size(1024 * 1024) == "1.0 MB"
        assert service._format_size(1024 * 1024 * 1024) == "1.0 GB"
