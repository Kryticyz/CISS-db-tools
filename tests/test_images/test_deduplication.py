"""
Tests for image deduplication module.
"""

from pathlib import Path

import pytest

from plantnet.images.deduplication import (
    DEFAULT_HAMMING_THRESHOLD,
    DEFAULT_HASH_SIZE,
    DeduplicationResult,
    compute_image_hash,
)


def test_deduplication_result_dataclass():
    """Test DeduplicationResult dataclass."""
    result = DeduplicationResult(
        species_name="Test_species",
        directory=Path("/tmp/test"),
        total_images=10,
        unique_images=10,
        duplicate_groups=0,
        duplicates_marked=0,
    )

    assert result.species_name == "Test_species"
    assert result.total_images == 10
    assert result.duplicate_groups == 0
    assert result.duplicates_marked == 0
    assert result.unique_images == 10
    assert result.has_duplicates == False


def test_default_constants():
    """Test that default constants are set correctly."""
    assert DEFAULT_HASH_SIZE == 16
    assert DEFAULT_HAMMING_THRESHOLD == 5


def test_compute_image_hash_invalid_path():
    """Test compute_image_hash with invalid path."""
    result = compute_image_hash(Path("/nonexistent/image.jpg"), hash_size=16)
    # Should return None or a tuple with error
    assert result is None or (len(result) == 3 and result[2] is not None)
