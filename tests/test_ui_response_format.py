"""
Tests to verify the UI infinite loop issue and API response format.

These tests confirm that the backend API returns the correct data format
that the frontend expects, helping diagnose the infinite "Analysing images" loop.
"""

import sys
import time
from pathlib import Path

import pytest

# Add scripts/images to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "images"))


def test_similarity_api_response_has_similar_groups():
    """Test that API returns data with similar_groups field."""
    from review_app.core.api import DetectionAPI
    from review_app.core.storage import init_faiss_store
    from review_duplicates_v2 import find_embeddings_dir

    # Initialize components
    embeddings_dir = find_embeddings_dir()
    faiss_store = init_faiss_store(embeddings_dir)

    if not faiss_store:
        pytest.skip("FAISS store not available")

    detection_api = DetectionAPI(faiss_store=faiss_store)
    base_dir = Path(
        "/Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species"
    )

    if not base_dir.exists():
        pytest.skip(f"Base directory not found: {base_dir}")

    # Make API call
    result = detection_api.get_species_cnn_similarity(
        base_dir, "Acacia_baileyana", 0.85, "resnet18"
    )

    # Verify response format matches what frontend expects
    assert "similar_groups" in result, "Missing 'similar_groups' field"
    assert isinstance(result["similar_groups"], list), "similar_groups should be a list"
    assert "species_name" in result, "Missing 'species_name' field"
    assert "total_images" in result, "Missing 'total_images' field"

    print(f"\n✓ Response format correct")
    print(f"  Keys: {list(result.keys())}")
    print(f"  From FAISS: {result.get('from_faiss', False)}")
    print(f"  Groups found: {len(result['similar_groups'])}")


def test_api_performance_with_faiss():
    """Regression: Ensure FAISS makes queries fast."""
    from review_app.core.api import DetectionAPI
    from review_app.core.storage import init_faiss_store
    from review_duplicates_v2 import find_embeddings_dir

    embeddings_dir = find_embeddings_dir()
    faiss_store = init_faiss_store(embeddings_dir)

    if not faiss_store:
        pytest.skip("FAISS store not available")

    detection_api = DetectionAPI(faiss_store=faiss_store)
    base_dir = Path(
        "/Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species"
    )

    if not base_dir.exists():
        pytest.skip(f"Base directory not found: {base_dir}")

    start = time.time()
    result = detection_api.get_species_cnn_similarity(
        base_dir, "Acacia_baileyana", 0.85, "resnet18"
    )
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Query took {elapsed:.2f}s (should be < 2s with FAISS)"
    assert result.get("from_faiss") == True, (
        "Should use FAISS, not on-demand computation"
    )
    print(f"\n✓ Query completed in {elapsed:.2f}s using FAISS")


def test_display_results_handles_error_responses():
    """
    Test that displayResults properly handles error responses.

    This is a placeholder for manual testing since it requires JavaScript execution.

    Manual test procedure:
    1. Start server: python review_duplicates_v2.py <base_dir>
    2. Open browser DevTools (F12)
    3. In Console, run: displayResults({error: "Test error"})
    4. Verify error message appears (not infinite spinner)
    """
    # This would require a JavaScript testing framework like Jest
    # For now, we document the manual test procedure
    pass


def test_similar_groups_structure():
    """Test that similar_groups has the expected structure."""
    from review_app.core.api import DetectionAPI
    from review_app.core.storage import init_faiss_store
    from review_duplicates_v2 import find_embeddings_dir

    embeddings_dir = find_embeddings_dir()
    faiss_store = init_faiss_store(embeddings_dir)

    if not faiss_store:
        pytest.skip("FAISS store not available")

    detection_api = DetectionAPI(faiss_store=faiss_store)
    base_dir = Path(
        "/Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species"
    )

    if not base_dir.exists():
        pytest.skip(f"Base directory not found: {base_dir}")

    result = detection_api.get_species_cnn_similarity(
        base_dir, "Acacia_baileyana", 0.85, "resnet18"
    )

    # Verify similar_groups structure
    similar_groups = result["similar_groups"]

    if len(similar_groups) > 0:
        group = similar_groups[0]
        assert "group_id" in group, "Group missing 'group_id'"
        assert "images" in group, "Group missing 'images'"
        assert "count" in group, "Group missing 'count'"
        assert isinstance(group["images"], list), "images should be a list"

        if len(group["images"]) > 0:
            img = group["images"][0]
            assert "filename" in img, "Image missing 'filename'"
            assert "path" in img, "Image missing 'path'"

        print(f"\n✓ similar_groups structure is correct")
        print(f"  First group has {group['count']} images")
    else:
        print(f"\n✓ No similar groups found (this is valid)")
