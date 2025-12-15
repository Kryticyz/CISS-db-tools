"""
Tests for image similarity module.
"""

from pathlib import Path

import pytest

from plantnet.images.similarity import (
    DEFAULT_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    SimilarityResult,
)


def test_similarity_result_dataclass():
    """Test SimilarityResult dataclass."""
    result = SimilarityResult(
        species_name="Test_species",
        directory=Path("/tmp/test"),
        total_images=10,
        processed_images=10,
        similar_groups=0,
        images_in_groups=0,
        similarity_threshold=0.85,
        model_name="resnet18",
    )

    assert result.species_name == "Test_species"
    assert result.total_images == 10
    assert result.similar_groups == 0
    assert result.similarity_threshold == 0.85
    assert result.model_name == "resnet18"


def test_default_constants():
    """Test that default constants are set correctly."""
    assert DEFAULT_MODEL == "resnet18"
    assert DEFAULT_SIMILARITY_THRESHOLD == 0.85
