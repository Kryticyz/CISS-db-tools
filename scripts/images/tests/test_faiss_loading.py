"""
Tests for FAISS vector database loading.

These tests verify that FAISS embeddings load correctly and
provide helpful error messages when they don't.
"""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_embeddings_path_current_vs_correct():
    """Verify the current (broken) path doesn't exist and correct path works."""
    # Change to project root for consistent testing
    project_root = Path(__file__).parent.parent.parent.parent
    os.chdir(project_root)

    # Current (broken) path from review_duplicates_v2.py
    broken_path = Path("data/databases/embeddings/plantnet_drive")
    assert not broken_path.exists(), (
        f"Broken path should not exist: {broken_path.absolute()}"
    )

    # Correct path (where embeddings actually are)
    correct_path = Path("data/databases/embeddings")
    assert correct_path.exists(), (
        f"Correct path should exist: {correct_path.absolute()}"
    )
    assert (correct_path / "embeddings.index").exists(), "embeddings.index should exist"
    assert (correct_path / "metadata.pkl").exists(), "metadata.pkl should exist"


def test_init_faiss_store_with_correct_path():
    """Test that FAISS loads successfully with the correct path."""
    from review_app.core.storage import init_faiss_store

    # Use absolute path to embeddings
    embeddings_path = Path(
        "/Users/kryticyz/Documents/life/CISS/plantNet/data/databases/embeddings"
    )

    if not embeddings_path.exists():
        pytest.skip(f"Embeddings not found at {embeddings_path}")

    # Should load successfully
    result = init_faiss_store(embeddings_path)
    assert result is not None, "FAISS should load successfully"
    assert hasattr(result, "index"), "Result should have index attribute"
    assert result.index.ntotal > 0, "Index should contain embeddings"

    # Verify it has a reasonable number of embeddings (at least 1000)
    actual_count = result.index.ntotal
    assert actual_count >= 1000, (
        f"Should have at least 1000 embeddings, got {actual_count}"
    )

    print(f"✓ Successfully loaded {actual_count} embeddings")


def test_init_faiss_store_with_broken_path():
    """Test that FAISS returns None with the broken path."""
    from review_app.core.storage import init_faiss_store

    # Use the broken path from review_duplicates_v2.py
    broken_path = Path("data/databases/embeddings/plantnet_drive")

    result = init_faiss_store(broken_path)
    assert result is None, "Should return None for non-existent path"


def test_init_faiss_store_shows_diagnostic_for_missing_path(capsys):
    """Test that helpful error messages are shown for missing paths."""
    from review_app.core.storage import init_faiss_store

    fake_path = Path("/nonexistent/path/to/embeddings")
    result = init_faiss_store(fake_path)

    assert result is None, "Should return None for non-existent path"

    # After Phase 2 fix, should print diagnostic message
    captured = capsys.readouterr()
    # This will pass after Phase 2 is implemented
    # For now, it may be empty (silent failure)


def test_init_faiss_store_missing_index_file(tmp_path, capsys):
    """Test behavior when directory exists but embeddings.index is missing."""
    from review_app.core.storage import init_faiss_store

    # Create directory but no index file
    embeddings_dir = tmp_path / "embeddings"
    embeddings_dir.mkdir()

    result = init_faiss_store(embeddings_dir)
    assert result is None, "Should return None when index file missing"

    # After Phase 2 fix, should print diagnostic about missing index
    captured = capsys.readouterr()
    # This will be checked after Phase 2 implementation


def test_init_faiss_store_missing_metadata(tmp_path, capsys):
    """Test behavior when index exists but metadata.pkl is missing."""
    from review_app.core.storage import init_faiss_store

    try:
        import faiss
        import numpy as np
    except ImportError:
        pytest.skip("FAISS not installed")

    embeddings_dir = tmp_path / "embeddings"
    embeddings_dir.mkdir()

    # Create index file but no metadata
    index = faiss.IndexFlatIP(512)
    index.add(np.random.rand(10, 512).astype("float32"))
    faiss.write_index(index, str(embeddings_dir / "embeddings.index"))

    # Should fail when trying to load (metadata missing)
    result = init_faiss_store(embeddings_dir)
    assert result is None, "Should return None when metadata missing"


def test_find_embeddings_dir_function():
    """Test the find_embeddings_dir() helper function (after Phase 3)."""
    # This test will be enabled after Phase 3 is implemented
    pytest.skip("Waiting for Phase 3 implementation")

    # After Phase 3:
    # from review_duplicates_v2 import find_embeddings_dir
    # result = find_embeddings_dir()
    # assert result.exists()
    # assert (result / "embeddings.index").exists()


def test_review_server_finds_embeddings():
    """Test that review server correctly finds embeddings (end-to-end)."""
    # This will work after Phase 3 is implemented
    pytest.skip("Waiting for Phase 3 implementation")

    # After Phase 3:
    # from review_duplicates_v2 import EMBEDDINGS_DIR
    # assert EMBEDDINGS_DIR.exists()
    # assert (EMBEDDINGS_DIR / "embeddings.index").exists()


def test_cli_embeddings_override():
    """Test that --embeddings CLI argument works (after Phase 4)."""
    # This will be enabled after Phase 4 is implemented
    pytest.skip("Waiting for Phase 4 implementation")

    # After Phase 4, test CLI argument:
    # Test that --embeddings flag overrides default path


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
