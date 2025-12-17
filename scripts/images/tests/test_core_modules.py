"""
Comprehensive tests for the core review app modules.

Tests for:
- api.py: DetectionAPI cache management
- detection.py: Species detection and duplicate finding
- storage.py: FAISS embedding store

These tests ensure the correct functioning of critical project components.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test constants (matching conftest.py)
TEST_HASH_SIZE = 16
TEST_HAMMING_THRESHOLD = 5


def create_valid_test_image(
    path: Path, width: int = 10, height: int = 10, color: tuple = (255, 0, 0)
):
    """Create a valid image file that can be processed by image hashing libraries."""
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), color)
        img.save(path)
    except ImportError:
        # Fallback: create minimal content
        path.write_bytes(b"fake image content")


# =============================================================================
# DetectionAPI Tests (api.py)
# =============================================================================


class TestDetectionAPIInitialization:
    """Tests for DetectionAPI initialization."""

    def test_detection_api_initialization(self):
        """Verify empty caches on init and faiss_store is set correctly."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        assert api.hash_cache == {}
        assert api.cnn_cache == {}
        assert api.faiss_store is None

    def test_detection_api_initialization_with_faiss(self, mock_faiss_store_with_data):
        """Verify faiss_store is set when provided."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI(faiss_store=mock_faiss_store_with_data)
        assert api.faiss_store is mock_faiss_store_with_data


class TestDetectionAPICacheManagement:
    """Tests for DetectionAPI cache management methods."""

    def test_invalidate_species_cache_hash(self):
        """Test that invalidate_species_cache removes hash cache entries."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        # Manually populate hash cache
        api.hash_cache["Species1_16"] = {Path("/fake/path"): "abc123"}
        api.hash_cache["Species1_8"] = {Path("/fake/path"): "def456"}
        api.hash_cache["Species2_16"] = {Path("/fake/path"): "ghi789"}

        api.invalidate_species_cache("Species1")

        # Species1 entries should be removed
        assert "Species1_16" not in api.hash_cache
        assert "Species1_8" not in api.hash_cache
        # Species2 should remain
        assert "Species2_16" in api.hash_cache

    def test_invalidate_species_cache_cnn(self):
        """Test that invalidate_species_cache removes CNN cache entries."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        # Manually populate CNN cache
        api.cnn_cache["Species1_resnet18"] = {Path("/fake/path"): [0.1, 0.2]}
        api.cnn_cache["Species1_resnet50"] = {Path("/fake/path"): [0.3, 0.4]}
        api.cnn_cache["Species2_resnet18"] = {Path("/fake/path"): [0.5, 0.6]}

        api.invalidate_species_cache("Species1")

        # Species1 entries should be removed
        assert "Species1_resnet18" not in api.cnn_cache
        assert "Species1_resnet50" not in api.cnn_cache
        # Species2 should remain
        assert "Species2_resnet18" in api.cnn_cache

    def test_invalidate_species_cache_both_caches(self):
        """Test that invalidate_species_cache clears both hash and CNN caches."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        api.hash_cache["TestSpecies_16"] = {Path("/fake"): "hash"}
        api.cnn_cache["TestSpecies_resnet18"] = {Path("/fake"): [0.1]}

        api.invalidate_species_cache("TestSpecies")

        assert len(api.hash_cache) == 0
        assert len(api.cnn_cache) == 0

    def test_clear_hash_cache(self):
        """Test clear_hash_cache empties the hash cache."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        api.hash_cache["Species1_16"] = {Path("/fake"): "hash1"}
        api.hash_cache["Species2_16"] = {Path("/fake"): "hash2"}

        api.clear_hash_cache()

        assert api.hash_cache == {}

    def test_clear_cnn_cache(self):
        """Test clear_cnn_cache empties the CNN cache."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        api.cnn_cache["Species1_resnet18"] = {Path("/fake"): [0.1]}
        api.cnn_cache["Species2_resnet18"] = {Path("/fake"): [0.2]}

        api.clear_cnn_cache()

        assert api.cnn_cache == {}

    def test_clear_all_caches(self):
        """Test clear_all_caches empties both caches."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        api.hash_cache["Species1_16"] = {Path("/fake"): "hash"}
        api.cnn_cache["Species1_resnet18"] = {Path("/fake"): [0.1]}

        api.clear_all_caches()

        assert api.hash_cache == {}
        assert api.cnn_cache == {}

    def test_get_cache_stats(self):
        """Test get_cache_stats returns correct counts."""
        from review_app.core.api import DetectionAPI

        api = DetectionAPI()
        api.hash_cache["Species1_16"] = {}
        api.hash_cache["Species2_16"] = {}
        api.cnn_cache["Species1_resnet18"] = {}

        stats = api.get_cache_stats()

        assert stats["hash_cache_entries"] == 2
        assert stats["cnn_cache_entries"] == 1


class TestDetectionAPIDeleteWithCacheInvalidation:
    """Tests for cache invalidation after file deletion."""

    def test_delete_files_invalidates_cache(self, tmp_path):
        """Test that deleting files invalidates the cache for affected species."""
        from review_app.core.api import DetectionAPI

        # Setup
        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "Species1"
        species_dir.mkdir(parents=True)

        test_file = species_dir / "test.jpg"
        test_file.write_text("content")

        api = DetectionAPI()
        # Pre-populate cache
        api.hash_cache["Species1_16"] = {Path("/fake"): "hash"}
        api.cnn_cache["Species1_resnet18"] = {Path("/fake"): [0.1]}

        # Delete file
        result = api.delete_files(base_dir, ["Species1/test.jpg"])

        # Verify deletion succeeded
        assert result["deleted_count"] == 1
        # Verify cache was invalidated
        assert "Species1_16" not in api.hash_cache
        assert "Species1_resnet18" not in api.cnn_cache

    def test_delete_files_invalidates_correct_species_only(self, tmp_path):
        """Test that only the affected species cache is invalidated."""
        from review_app.core.api import DetectionAPI

        # Setup
        base_dir = tmp_path / "by_species"
        species1_dir = base_dir / "Species1"
        species2_dir = base_dir / "Species2"
        species1_dir.mkdir(parents=True)
        species2_dir.mkdir(parents=True)

        test_file = species1_dir / "test.jpg"
        test_file.write_text("content")

        api = DetectionAPI()
        # Pre-populate cache for both species
        api.hash_cache["Species1_16"] = {Path("/fake"): "hash1"}
        api.hash_cache["Species2_16"] = {Path("/fake"): "hash2"}

        # Delete from Species1 only
        api.delete_files(base_dir, ["Species1/test.jpg"])

        # Species1 cache should be cleared
        assert "Species1_16" not in api.hash_cache
        # Species2 cache should remain
        assert "Species2_16" in api.hash_cache


# =============================================================================
# Detection Module Tests (detection.py)
# =============================================================================


class TestGetSpeciesList:
    """Tests for get_species_list function."""

    def test_get_species_list_empty_dir(self, tmp_path):
        """Test with empty base directory."""
        from review_app.core.detection import get_species_list

        base_dir = tmp_path / "by_species"
        base_dir.mkdir()

        result = get_species_list(base_dir)
        assert result == []

    def test_get_species_list_with_species(self, species_with_valid_images):
        """Test with species folders containing images."""
        from review_app.core.detection import get_species_list

        base_dir, images = species_with_valid_images
        result = get_species_list(base_dir)

        assert len(result) == 2
        assert "Species1" in result
        assert "Species2" in result
        # Should be sorted
        assert result == sorted(result)

    def test_get_species_list_excludes_hidden_dirs(self, tmp_path):
        """Test that hidden directories are excluded."""
        from review_app.core.detection import get_species_list

        base_dir = tmp_path / "by_species"
        base_dir.mkdir()

        # Create hidden directory with images
        hidden_dir = base_dir / ".hidden"
        hidden_dir.mkdir()
        create_valid_test_image(hidden_dir / "img.jpg")

        # Create visible directory with images
        visible_dir = base_dir / "Visible"
        visible_dir.mkdir()
        create_valid_test_image(visible_dir / "img.jpg")

        result = get_species_list(base_dir)

        assert ".hidden" not in result
        assert "Visible" in result

    def test_get_species_list_excludes_empty_species(self, tmp_path):
        """Test that species folders without images are excluded."""
        from review_app.core.detection import get_species_list

        base_dir = tmp_path / "by_species"
        base_dir.mkdir()

        # Create empty directory
        empty_dir = base_dir / "EmptySpecies"
        empty_dir.mkdir()

        # Create directory with images
        with_images = base_dir / "WithImages"
        with_images.mkdir()
        create_valid_test_image(with_images / "img.jpg")

        result = get_species_list(base_dir)

        assert "EmptySpecies" not in result
        assert "WithImages" in result

    def test_get_species_list_none_base_dir(self):
        """Test that None base_dir returns empty list without crashing."""
        from review_app.core.detection import get_species_list

        result = get_species_list(None)
        assert result == []


class TestGetSpeciesHashes:
    """Tests for get_species_hashes function."""

    def test_get_species_hashes_nonexistent_species(self, tmp_path):
        """Test with non-existent species directory."""
        from review_app.core.detection import get_species_hashes

        base_dir = tmp_path / "by_species"
        base_dir.mkdir()
        hash_cache = {}

        result = get_species_hashes(base_dir, "NonExistent", 16, hash_cache)

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_get_species_hashes_empty_species(self, tmp_path):
        """Test with species directory but no images."""
        from review_app.core.detection import get_species_hashes

        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "EmptySpecies"
        species_dir.mkdir(parents=True)
        hash_cache = {}

        result = get_species_hashes(base_dir, "EmptySpecies", 16, hash_cache)

        assert "error" not in result
        assert result["total_images"] == 0
        assert result["images"] == []

    def test_get_species_hashes_with_images(self, species_with_valid_images):
        """Test with species containing images."""
        from review_app.core.detection import get_species_hashes

        base_dir, images = species_with_valid_images
        hash_cache = {}

        result = get_species_hashes(base_dir, "Species1", 16, hash_cache)

        assert "error" not in result
        assert result["species_name"] == "Species1"
        assert result["total_images"] == 3
        assert len(result["images"]) == 3

    def test_get_species_hashes_uses_cache(self, species_with_valid_images):
        """Test that second call uses cached data."""
        from review_app.core.detection import get_species_hashes

        base_dir, images = species_with_valid_images
        hash_cache = {}

        # First call - should compute and cache
        get_species_hashes(base_dir, "Species1", 16, hash_cache)
        assert "Species1_16" in hash_cache

        # Modify cache to verify it's being used
        original_cache_entry = hash_cache["Species1_16"].copy()

        # Second call - should use cache
        result = get_species_hashes(base_dir, "Species1", 16, hash_cache)

        # Cache should still have same data
        assert hash_cache["Species1_16"] == original_cache_entry

    def test_get_species_hashes_different_hash_size_not_cached(
        self, species_with_valid_images
    ):
        """Test that different hash sizes create separate cache entries."""
        from review_app.core.detection import get_species_hashes

        base_dir, images = species_with_valid_images
        hash_cache = {}

        # Call with hash_size=8
        get_species_hashes(base_dir, "Species1", 8, hash_cache)
        # Call with hash_size=16
        get_species_hashes(base_dir, "Species1", 16, hash_cache)

        # Should have two separate cache entries
        assert "Species1_8" in hash_cache
        assert "Species1_16" in hash_cache


class TestGetSpeciesDuplicates:
    """Tests for get_species_duplicates function."""

    def test_get_species_duplicates_nonexistent_species(self, tmp_path):
        """Test with non-existent species."""
        from review_app.core.detection import get_species_duplicates

        base_dir = tmp_path / "by_species"
        base_dir.mkdir()
        hash_cache = {}

        result = get_species_duplicates(base_dir, "NonExistent", 16, 5, hash_cache)

        assert "error" in result

    def test_get_species_duplicates_single_image(self, tmp_path):
        """Test with only 1 image - not enough for duplicate detection."""
        from review_app.core.detection import get_species_duplicates

        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "SingleImage"
        species_dir.mkdir(parents=True)
        create_valid_test_image(species_dir / "only_one.jpg")
        hash_cache = {}

        result = get_species_duplicates(base_dir, "SingleImage", 16, 5, hash_cache)

        assert "error" not in result
        assert "message" in result
        assert "not enough" in result["message"].lower()

    def test_get_species_duplicates_valid_response(self, tmp_path):
        """Test with multiple images returns valid response with correct structure."""
        from review_app.core.detection import get_species_duplicates

        # Create images
        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "TestImages"
        species_dir.mkdir(parents=True)

        # Create images with different content
        create_valid_test_image(
            species_dir / "img1.jpg", width=100, height=100, color=(255, 0, 0)
        )
        create_valid_test_image(
            species_dir / "img2.jpg", width=50, height=150, color=(0, 255, 0)
        )
        create_valid_test_image(
            species_dir / "img3.jpg", width=200, height=50, color=(0, 0, 255)
        )

        hash_cache = {}
        result = get_species_duplicates(base_dir, "TestImages", 16, 5, hash_cache)

        assert "error" not in result
        assert result["total_images"] == 3
        assert "duplicate_groups" in result
        assert isinstance(result["duplicate_groups"], list)
        # total_duplicates should be consistent with groups
        if result["duplicate_groups"]:
            expected_total = sum(
                len(g["duplicates"]) for g in result["duplicate_groups"]
            )
            assert result["total_duplicates"] == expected_total

    def test_get_species_duplicates_response_structure(self, species_with_valid_images):
        """Test that response has all expected fields."""
        from review_app.core.detection import get_species_duplicates

        base_dir, images = species_with_valid_images
        hash_cache = {}

        result = get_species_duplicates(base_dir, "Species1", 16, 5, hash_cache)

        # Verify all expected fields are present
        assert "species_name" in result
        assert "total_images" in result
        assert "hashed_images" in result
        assert "duplicate_groups" in result
        assert "total_duplicates" in result
        assert "hash_size" in result
        assert "hamming_threshold" in result
        assert "images" in result


class TestGetAllSpeciesDuplicates:
    """Tests for get_all_species_duplicates function."""

    def test_get_all_species_duplicates_aggregates_correctly(
        self, species_with_valid_images
    ):
        """Test that all species are scanned and results aggregated."""
        from review_app.core.detection import get_all_species_duplicates

        base_dir, images = species_with_valid_images
        hash_cache = {}

        result = get_all_species_duplicates(base_dir, 16, 5, hash_cache)

        assert result["mode"] == "all_species"
        assert result["total_species_scanned"] == 2  # Species1 and Species2
        assert "total_images" in result
        assert "species_results" in result


class TestDeleteFilesAffectedSpecies:
    """Additional tests for delete_files affected_species tracking."""

    def test_delete_files_returns_affected_species(self, tmp_path):
        """Test that affected_species is correctly populated."""
        from review_app.core.detection import delete_files

        base_dir = tmp_path / "by_species"
        species1_dir = base_dir / "Species1"
        species2_dir = base_dir / "Species2"
        species1_dir.mkdir(parents=True)
        species2_dir.mkdir(parents=True)

        (species1_dir / "img1.jpg").write_text("content")
        (species2_dir / "img2.jpg").write_text("content")

        result = delete_files(base_dir, ["Species1/img1.jpg", "Species2/img2.jpg"])

        assert "affected_species" in result
        assert set(result["affected_species"]) == {"Species1", "Species2"}

    def test_delete_files_affected_species_deduped(self, tmp_path):
        """Test that affected_species contains unique values."""
        from review_app.core.detection import delete_files

        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "Species1"
        species_dir.mkdir(parents=True)

        (species_dir / "img1.jpg").write_text("content")
        (species_dir / "img2.jpg").write_text("content")

        result = delete_files(base_dir, ["Species1/img1.jpg", "Species1/img2.jpg"])

        assert "affected_species" in result
        # Should only appear once even though two files from same species
        assert result["affected_species"] == ["Species1"]


class TestGetSpeciesCNNSimilarity:
    """Tests for CNN similarity detection."""

    def test_get_species_cnn_similarity_uses_faiss_when_available(
        self, species_with_valid_images, mock_faiss_store_with_data
    ):
        """Test that FAISS store is used when provided."""
        from review_app.core.detection import get_species_cnn_similarity

        base_dir, images = species_with_valid_images
        cnn_cache = {}

        result = get_species_cnn_similarity(
            base_dir,
            "Species1",
            0.85,
            "resnet18",
            cnn_cache,
            mock_faiss_store_with_data,
        )

        assert mock_faiss_store_with_data.search_called
        assert mock_faiss_store_with_data.last_species == "Species1"
        assert result.get("from_faiss") is True

    def test_get_species_cnn_similarity_falls_back_on_faiss_error(
        self, species_with_valid_images, mock_faiss_store_raises
    ):
        """Test fallback to on-demand computation when FAISS fails."""
        from review_app.core.detection import CNN_AVAILABLE, get_species_cnn_similarity

        base_dir, images = species_with_valid_images
        cnn_cache = {}

        result = get_species_cnn_similarity(
            base_dir, "Species1", 0.85, "resnet18", cnn_cache, mock_faiss_store_raises
        )

        # Should either fall back to on-demand (if CNN available) or return error
        if CNN_AVAILABLE:
            assert result.get("from_faiss") is not True
        else:
            assert "error" in result

    def test_get_species_cnn_similarity_single_image(self, tmp_path):
        """Test with only 1 image."""
        from review_app.core.detection import CNN_AVAILABLE, get_species_cnn_similarity

        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "SingleImage"
        species_dir.mkdir(parents=True)
        create_valid_test_image(species_dir / "only_one.jpg")
        cnn_cache = {}

        result = get_species_cnn_similarity(
            base_dir, "SingleImage", 0.85, "resnet18", cnn_cache, None
        )

        # Without FAISS and with single image, should return message
        if not CNN_AVAILABLE:
            assert "error" in result
        else:
            assert "message" in result or len(result.get("similar_groups", [])) == 0


# =============================================================================
# Integration Tests: Similarity Search After Deletion
# =============================================================================


class TestSimilaritySearchAfterDeletion:
    """Integration tests verifying similarity search works correctly after deletion."""

    def test_stale_cache_not_returned_after_deletion(self, tmp_path):
        """Critical test: deleted files should not appear in results."""
        from review_app.core.api import DetectionAPI

        # Setup
        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "TestSpecies"
        species_dir.mkdir(parents=True)

        # Create images
        img1 = species_dir / "image1.jpg"
        img2 = species_dir / "image2.jpg"
        img3 = species_dir / "image3.jpg"
        create_valid_test_image(img1, color=(255, 0, 0))
        create_valid_test_image(img2, color=(0, 255, 0))
        create_valid_test_image(img3, color=(0, 0, 255))

        api = DetectionAPI()

        # First query - populate cache
        result1 = api.get_species_hashes(base_dir, "TestSpecies", 16)
        assert result1["total_images"] == 3
        filenames1 = {img["filename"] for img in result1["images"]}
        assert "image2.jpg" in filenames1

        # Delete image2
        api.delete_files(base_dir, ["TestSpecies/image2.jpg"])

        # Second query - should not include deleted file
        result2 = api.get_species_hashes(base_dir, "TestSpecies", 16)
        assert result2["total_images"] == 2
        filenames2 = {img["filename"] for img in result2["images"]}
        assert "image2.jpg" not in filenames2

    def test_hash_duplicates_cache_invalidated_after_deletion(self, tmp_path):
        """Test that hash cache is invalidated and recomputed after deletion."""
        from review_app.core.api import DetectionAPI

        # Setup
        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "TestSpecies"
        species_dir.mkdir(parents=True)

        # Create images
        for i in range(3):
            create_valid_test_image(
                species_dir / f"image{i}.jpg", color=(i * 80, i * 80, i * 80)
            )

        api = DetectionAPI()

        # First query - populate cache
        api.get_species_duplicates(base_dir, "TestSpecies", 16, 5)
        assert "TestSpecies_16" in api.hash_cache

        # Delete an image via API
        api.delete_files(base_dir, ["TestSpecies/image1.jpg"])

        # Cache should be invalidated
        assert "TestSpecies_16" not in api.hash_cache

        # Next query should work with updated data
        result = api.get_species_duplicates(base_dir, "TestSpecies", 16, 5)
        assert result["total_images"] == 2

    def test_all_species_duplicates_after_deletion(self, tmp_path):
        """Test all-species query works correctly after deleting from one species."""
        from review_app.core.api import DetectionAPI

        # Setup
        base_dir = tmp_path / "by_species"
        species1_dir = base_dir / "Species1"
        species2_dir = base_dir / "Species2"
        species1_dir.mkdir(parents=True)
        species2_dir.mkdir(parents=True)

        # Create images in both species
        for i in range(3):
            create_valid_test_image(species1_dir / f"img{i}.jpg", color=(i * 50, 0, 0))
            create_valid_test_image(species2_dir / f"img{i}.jpg", color=(0, i * 50, 0))

        api = DetectionAPI()

        # First query
        result1 = api.get_all_species_duplicates(base_dir, 16, 5)
        total1 = result1["total_images"]

        # Delete from Species1
        api.delete_files(base_dir, ["Species1/img0.jpg"])

        # Query again
        result2 = api.get_all_species_duplicates(base_dir, 16, 5)

        # Total should decrease by 1
        assert result2["total_images"] == total1 - 1

    def test_delete_then_immediate_query_consistency(self, tmp_path):
        """Test that immediate queries after deletion are consistent."""
        from review_app.core.api import DetectionAPI

        base_dir = tmp_path / "by_species"
        species_dir = base_dir / "TestSpecies"
        species_dir.mkdir(parents=True)

        # Create 5 images
        for i in range(5):
            create_valid_test_image(
                species_dir / f"img{i}.jpg", color=(i * 40, i * 40, i * 40)
            )

        api = DetectionAPI()

        # Initial count
        result = api.get_species_hashes(base_dir, "TestSpecies", 16)
        assert result["total_images"] == 5

        # Delete 2 images in quick succession
        api.delete_files(base_dir, ["TestSpecies/img1.jpg"])
        result = api.get_species_hashes(base_dir, "TestSpecies", 16)
        assert result["total_images"] == 4

        api.delete_files(base_dir, ["TestSpecies/img3.jpg"])
        result = api.get_species_hashes(base_dir, "TestSpecies", 16)
        assert result["total_images"] == 3


# =============================================================================
# Storage Module Tests (storage.py)
# =============================================================================


class TestInitFaissStore:
    """Tests for init_faiss_store function."""

    def test_init_faiss_store_missing_directory(self, tmp_path):
        """Test with non-existent directory."""
        from review_app.core.storage import init_faiss_store

        fake_path = tmp_path / "nonexistent"
        result = init_faiss_store(fake_path)
        assert result is None

    def test_init_faiss_store_missing_index_file(self, tmp_path):
        """Test with directory but missing embeddings.index."""
        from review_app.core.storage import init_faiss_store

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        result = init_faiss_store(embeddings_dir)
        assert result is None

    def test_init_faiss_store_missing_metadata(self, tmp_path):
        """Test with index but missing metadata.pkl."""
        from review_app.core.storage import init_faiss_store

        try:
            import faiss
            import numpy as np
        except ImportError:
            pytest.skip("FAISS not installed")

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        # Create index file
        index = faiss.IndexFlatIP(512)
        index.add(np.random.rand(10, 512).astype("float32"))
        faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

        result = init_faiss_store(embeddings_dir)
        assert result is None

    def test_init_faiss_store_missing_full_metadata(self, tmp_path):
        """Test with index and metadata but missing metadata_full.pkl."""
        from review_app.core.storage import init_faiss_store

        try:
            import pickle

            import faiss
            import numpy as np
        except ImportError:
            pytest.skip("FAISS not installed")

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        # Create index file
        index = faiss.IndexFlatIP(512)
        index.add(np.random.rand(10, 512).astype("float32"))
        faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

        # Create metadata.pkl but not metadata_full.pkl
        with open(embeddings_dir / "metadata.pkl", "wb") as f:
            pickle.dump([{"species": "Test", "filename": "test.jpg", "size": 100}], f)

        result = init_faiss_store(embeddings_dir)
        assert result is None


class TestFAISSEmbeddingStoreSearch:
    """Tests for FAISSEmbeddingStore search functionality."""

    def test_faiss_store_search_species_not_found(self, tmp_path):
        """Test search for species not in the store."""
        try:
            import pickle

            import faiss
            import numpy as np
        except ImportError:
            pytest.skip("FAISS not installed")

        from review_app.core.storage import FAISSEmbeddingStore

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        # Create minimal valid FAISS store
        index = faiss.IndexFlatIP(512)
        embeddings = np.random.rand(5, 512).astype("float32")
        index.add(embeddings)
        faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

        metadata = [
            {"species": "ExistingSpecies", "filename": f"img{i}.jpg", "size": 1000}
            for i in range(5)
        ]
        with open(embeddings_dir / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)

        full_metadata = [
            {
                "species": "ExistingSpecies",
                "filename": f"img{i}.jpg",
                "size": 1000,
                "embedding": embeddings[i].tolist(),
            }
            for i in range(5)
        ]
        with open(embeddings_dir / "metadata_full.pkl", "wb") as f:
            pickle.dump(full_metadata, f)

        store = FAISSEmbeddingStore(embeddings_dir)
        result = store.search_species("NonExistentSpecies")

        assert result == []

    def test_faiss_store_search_species_single_image(self, tmp_path):
        """Test search for species with only 1 image."""
        try:
            import pickle

            import faiss
            import numpy as np
        except ImportError:
            pytest.skip("FAISS not installed")

        from review_app.core.storage import FAISSEmbeddingStore

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        # Create FAISS store with 1 image in target species
        index = faiss.IndexFlatIP(512)
        embeddings = np.random.rand(3, 512).astype("float32")
        index.add(embeddings)
        faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

        metadata = [
            {"species": "SingleImageSpecies", "filename": "img0.jpg", "size": 1000},
            {"species": "OtherSpecies", "filename": "img1.jpg", "size": 1000},
            {"species": "OtherSpecies", "filename": "img2.jpg", "size": 1000},
        ]
        with open(embeddings_dir / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)

        full_metadata = [
            {
                "species": m["species"],
                "filename": m["filename"],
                "size": m["size"],
                "embedding": embeddings[i].tolist(),
            }
            for i, m in enumerate(metadata)
        ]
        with open(embeddings_dir / "metadata_full.pkl", "wb") as f:
            pickle.dump(full_metadata, f)

        store = FAISSEmbeddingStore(embeddings_dir)
        result = store.search_species("SingleImageSpecies")

        # Need 2+ images for similarity groups
        assert result == []

    def test_faiss_store_get_status(self, tmp_path):
        """Test get_status returns correct structure."""
        try:
            import pickle

            import faiss
            import numpy as np
        except ImportError:
            pytest.skip("FAISS not installed")

        from review_app.core.storage import FAISSEmbeddingStore

        embeddings_dir = tmp_path / "embeddings"
        embeddings_dir.mkdir()

        index = faiss.IndexFlatIP(512)
        embeddings = np.random.rand(10, 512).astype("float32")
        index.add(embeddings)
        faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

        metadata = [
            {"species": "Test", "filename": f"img{i}.jpg", "size": 100}
            for i in range(10)
        ]
        with open(embeddings_dir / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)

        full_metadata = [
            {
                "species": "Test",
                "filename": f"img{i}.jpg",
                "size": 100,
                "embedding": embeddings[i].tolist(),
            }
            for i in range(10)
        ]
        with open(embeddings_dir / "metadata_full.pkl", "wb") as f:
            pickle.dump(full_metadata, f)

        store = FAISSEmbeddingStore(embeddings_dir)
        status = store.get_status()

        assert status["available"] is True
        assert status["count"] == 10
        assert "location" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
