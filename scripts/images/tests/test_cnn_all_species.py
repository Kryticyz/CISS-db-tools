"""
Tests for CNN all species functionality.

Tests the get_all_species_cnn_similarity() function and
the /api/similarity/all endpoint.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_get_all_species_cnn_similarity_exists():
    """Test that the function exists and is importable."""
    from review_app.core.detection import get_all_species_cnn_similarity

    assert callable(get_all_species_cnn_similarity)


def test_get_all_species_cnn_similarity_signature():
    """Test that the function has the correct signature."""
    import inspect

    from review_app.core.detection import get_all_species_cnn_similarity

    sig = inspect.signature(get_all_species_cnn_similarity)
    params = list(sig.parameters.keys())

    # Check required parameters
    assert "base_dir" in params
    assert "similarity_threshold" in params
    assert "model_name" in params
    assert "cnn_cache" in params
    assert "faiss_store" in params


def test_get_all_species_cnn_similarity_empty_directory(tmp_path):
    """Test function with empty directory."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache={},
        faiss_store=None,
    )

    # Should return valid structure with no results
    assert isinstance(result, dict)
    assert result["mode"] == "all_species_cnn"
    assert result["total_species_scanned"] == 0
    assert result["species_with_similarities"] == 0
    assert result["total_images"] == 0
    assert result["total_groups"] == 0
    assert result["species_results"] == []


def test_get_all_species_cnn_similarity_with_species(tmp_path):
    """Test function with multiple species folders."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create multiple species folders
    for i in range(3):
        species_dir = base_dir / f"Species{i}"
        species_dir.mkdir()

        # Create a few image files
        for j in range(2):
            img_file = species_dir / f"img{j}.jpg"
            img_file.write_bytes(b"fake image data")

    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache={},
        faiss_store=None,
    )

    # Should scan all species
    assert result["mode"] == "all_species_cnn"
    assert result["total_species_scanned"] == 3
    assert result["similarity_threshold"] == 0.85
    assert result["model_name"] == "resnet18"
    assert isinstance(result["species_results"], list)


def test_get_all_species_cnn_similarity_return_structure():
    """Test that the function returns the expected structure."""
    # Create a minimal test
    import tempfile
    from pathlib import Path

    from review_app.core.detection import get_all_species_cnn_similarity

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "by_species"
        base_dir.mkdir()

        result = get_all_species_cnn_similarity(
            base_dir=base_dir,
            similarity_threshold=0.85,
            model_name="resnet18",
            cnn_cache={},
            faiss_store=None,
        )

        # Verify all required keys are present
        required_keys = [
            "mode",
            "total_species_scanned",
            "species_with_similarities",
            "total_images",
            "total_groups",
            "similarity_threshold",
            "model_name",
            "species_results",
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"


def test_api_wrapper_has_method():
    """Test that DetectionAPI has the all species method."""
    from review_app.core.api import DetectionAPI

    api = DetectionAPI()
    assert hasattr(api, "get_all_species_cnn_similarity")
    assert callable(api.get_all_species_cnn_similarity)


def test_api_wrapper_method_works(tmp_path):
    """Test that the API wrapper method works correctly."""
    from review_app.core.api import DetectionAPI

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create a species folder
    species_dir = base_dir / "TestSpecies"
    species_dir.mkdir()
    (species_dir / "img.jpg").write_bytes(b"data")

    api = DetectionAPI()
    result = api.get_all_species_cnn_similarity(
        base_dir=base_dir, similarity_threshold=0.85, model_name="resnet18"
    )

    # Should return valid result
    assert isinstance(result, dict)
    assert result["mode"] == "all_species_cnn"
    assert result["total_species_scanned"] == 1


def test_function_exported_in_init():
    """Test that the function is exported in __init__.py."""
    from review_app.core import get_all_species_cnn_similarity

    assert callable(get_all_species_cnn_similarity)


def test_threshold_parameter_respected(tmp_path):
    """Test that the similarity threshold parameter is stored in result."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Test with different thresholds
    for threshold in [0.5, 0.75, 0.85, 0.95]:
        result = get_all_species_cnn_similarity(
            base_dir=base_dir,
            similarity_threshold=threshold,
            model_name="resnet18",
            cnn_cache={},
            faiss_store=None,
        )

        assert result["similarity_threshold"] == threshold


def test_model_name_parameter_respected(tmp_path):
    """Test that the model name parameter is stored in result."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Test with different models
    for model in ["resnet18", "resnet50", "vgg16"]:
        result = get_all_species_cnn_similarity(
            base_dir=base_dir,
            similarity_threshold=0.85,
            model_name=model,
            cnn_cache={},
            faiss_store=None,
        )

        assert result["model_name"] == model


def test_cnn_cache_parameter_accepted(tmp_path):
    """Test that the function accepts and uses cnn_cache parameter."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create a species folder with an image
    species_dir = base_dir / "TestSpecies"
    species_dir.mkdir()
    (species_dir / "img.jpg").write_bytes(b"fake data")

    # Should work with empty cache
    cache = {}
    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache=cache,
        faiss_store=None,
    )

    assert isinstance(result, dict)


def test_aggregates_multiple_species_correctly(tmp_path):
    """Test that the function correctly aggregates results from multiple species."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create 5 species folders
    species_count = 5
    for i in range(species_count):
        species_dir = base_dir / f"Species_{i}"
        species_dir.mkdir()

        # Add some images
        for j in range(3):
            img_file = species_dir / f"image_{j}.jpg"
            img_file.write_bytes(b"fake image")

    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache={},
        faiss_store=None,
    )

    # Should have scanned all species
    assert result["total_species_scanned"] == species_count
    assert result["mode"] == "all_species_cnn"


def test_species_results_is_list(tmp_path):
    """Test that species_results is always a list."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache={},
        faiss_store=None,
    )

    assert isinstance(result["species_results"], list)


def test_handles_species_with_no_images(tmp_path):
    """Test that empty species folders don't cause errors."""
    from review_app.core.detection import get_all_species_cnn_similarity

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create species folders, some empty, some with images
    (base_dir / "EmptySpecies1").mkdir()
    (base_dir / "EmptySpecies2").mkdir()

    species_with_images = base_dir / "SpeciesWithImages"
    species_with_images.mkdir()
    (species_with_images / "img.jpg").write_bytes(b"data")

    result = get_all_species_cnn_similarity(
        base_dir=base_dir,
        similarity_threshold=0.85,
        model_name="resnet18",
        cnn_cache={},
        faiss_store=None,
    )

    # Should only scan species with images (empty folders are skipped by get_species_list)
    assert result["total_species_scanned"] == 1
    assert isinstance(result, dict)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
