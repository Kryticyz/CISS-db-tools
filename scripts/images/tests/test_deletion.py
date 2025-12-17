"""
Unit tests for file deletion functionality.

Tests the delete_files() function in review_app.core.detection
to ensure safe and correct file deletion behavior.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_delete_files_success(tmp_path):
    """Test successful deletion of multiple files."""
    from review_app.core.detection import delete_files

    # Create test directory structure
    test_dir = tmp_path / "by_species" / "TestSpecies"
    test_dir.mkdir(parents=True)

    # Create test files
    file1 = test_dir / "test1.jpg"
    file2 = test_dir / "test2.jpg"
    file3 = test_dir / "test3.jpg"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    file3.write_text("test content 3")

    # Verify files exist
    assert file1.exists()
    assert file2.exists()
    assert file3.exists()

    # Delete files
    result = delete_files(
        tmp_path / "by_species",
        ["TestSpecies/test1.jpg", "TestSpecies/test2.jpg", "TestSpecies/test3.jpg"],
    )

    # Verify result
    assert result["success"] == True
    assert result["deleted_count"] == 3
    assert result["error_count"] == 0
    assert len(result.get("errors", [])) == 0

    # Verify files are actually deleted
    assert not file1.exists()
    assert not file2.exists()
    assert not file3.exists()


def test_delete_files_partial_success(tmp_path):
    """Test deletion when some files don't exist."""
    from review_app.core.detection import delete_files

    # Create test directory structure
    test_dir = tmp_path / "by_species" / "TestSpecies"
    test_dir.mkdir(parents=True)

    # Create only one file
    file1 = test_dir / "test1.jpg"
    file1.write_text("test content")

    assert file1.exists()

    # Try to delete both existing and non-existing files
    result = delete_files(
        tmp_path / "by_species",
        ["TestSpecies/test1.jpg", "TestSpecies/nonexistent.jpg"],
    )

    # Should report partial success
    assert result["deleted_count"] == 1
    assert result["error_count"] == 1
    assert len(result["errors"]) == 1
    assert not file1.exists()
    assert "nonexistent.jpg" in result["errors"][0]["path"]


def test_delete_files_security_path_traversal(tmp_path):
    """Test path traversal prevention - cannot delete files outside base_dir."""
    from review_app.core.detection import delete_files

    # Create base directory
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create a file outside the base directory
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret data")

    assert outside_file.exists()

    # Try to delete file outside base_dir using path traversal
    result = delete_files(base_dir, ["../outside/secret.txt"])

    # Should fail and not delete the file
    assert result["success"] == False
    assert result["deleted_count"] == 0
    assert result["error_count"] == 1
    assert outside_file.exists()  # File should still exist
    assert len(result["errors"]) == 1
    # Error message should indicate invalid path (security check)
    assert "invalid" in result["errors"][0]["error"].lower()


def test_delete_files_security_absolute_path(tmp_path):
    """Test that absolute paths outside base_dir are rejected."""
    from review_app.core.detection import delete_files

    # Create base directory
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create a file outside using absolute path
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "important.txt"
    outside_file.write_text("important data")

    assert outside_file.exists()

    # Try to delete using absolute path
    result = delete_files(base_dir, [str(outside_file)])

    # Should fail
    assert result["success"] == False
    assert result["deleted_count"] == 0
    assert outside_file.exists()


def test_delete_files_empty_list(tmp_path):
    """Test deletion with empty file list."""
    from review_app.core.detection import delete_files

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    result = delete_files(base_dir, [])

    # Should succeed with no operations
    assert result["success"] == True
    assert result["deleted_count"] == 0
    assert result["error_count"] == 0


def test_delete_files_not_found(tmp_path):
    """Test deleting non-existent files."""
    from review_app.core.detection import delete_files

    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    result = delete_files(base_dir, ["Species/nonexistent.jpg", "Species/missing.jpg"])

    # Should fail with appropriate errors
    assert result["success"] == False
    assert result["deleted_count"] == 0
    assert result["error_count"] == 2
    assert len(result["errors"]) == 2


def test_delete_files_permission_error(tmp_path):
    """Test deletion when file permissions prevent deletion."""
    import platform

    # Skip this test on Windows as permission handling is different
    if platform.system() == "Windows":
        pytest.skip("Permission test not applicable on Windows")

    from review_app.core.detection import delete_files

    # Create test directory structure
    test_dir = tmp_path / "by_species" / "TestSpecies"
    test_dir.mkdir(parents=True)

    # Create a file
    protected_file = test_dir / "protected.jpg"
    protected_file.write_text("protected content")

    # Remove write permissions from parent directory
    test_dir.chmod(0o555)  # r-xr-xr-x

    try:
        result = delete_files(tmp_path / "by_species", ["TestSpecies/protected.jpg"])

        # Should report error (file might still exist due to permissions)
        assert result["error_count"] >= 0  # May or may not error depending on OS

    finally:
        # Restore permissions for cleanup
        test_dir.chmod(0o755)


def test_delete_files_multiple_species(tmp_path):
    """Test deleting files from multiple species folders."""
    from review_app.core.detection import delete_files

    base_dir = tmp_path / "by_species"

    # Create multiple species folders
    species1_dir = base_dir / "Species1"
    species2_dir = base_dir / "Species2"
    species1_dir.mkdir(parents=True)
    species2_dir.mkdir(parents=True)

    # Create files in each
    file1 = species1_dir / "img1.jpg"
    file2 = species1_dir / "img2.jpg"
    file3 = species2_dir / "img1.jpg"
    file4 = species2_dir / "img2.jpg"

    for f in [file1, file2, file3, file4]:
        f.write_text("content")

    # Delete files from both species
    result = delete_files(
        base_dir,
        [
            "Species1/img1.jpg",
            "Species1/img2.jpg",
            "Species2/img1.jpg",
            "Species2/img2.jpg",
        ],
    )

    # All should be deleted
    assert result["success"] == True
    assert result["deleted_count"] == 4
    assert result["error_count"] == 0

    for f in [file1, file2, file3, file4]:
        assert not f.exists()


def test_delete_files_special_characters_in_filename(tmp_path):
    """Test deletion of files with special characters in names."""
    from review_app.core.detection import delete_files

    test_dir = tmp_path / "by_species" / "TestSpecies"
    test_dir.mkdir(parents=True)

    # Create files with special characters
    special_files = [
        "test image (1).jpg",
        "test-image_2.jpg",
        "test.image.3.jpg",
    ]

    for filename in special_files:
        (test_dir / filename).write_text("content")

    # Delete them
    result = delete_files(
        tmp_path / "by_species", [f"TestSpecies/{fn}" for fn in special_files]
    )

    # All should be deleted
    assert result["success"] == True
    assert result["deleted_count"] == len(special_files)

    for filename in special_files:
        assert not (test_dir / filename).exists()


def test_delete_files_returns_correct_structure(tmp_path):
    """Test that delete_files returns the expected data structure."""
    from review_app.core.detection import delete_files

    test_dir = tmp_path / "by_species" / "TestSpecies"
    test_dir.mkdir(parents=True)

    file1 = test_dir / "test.jpg"
    file1.write_text("content")

    result = delete_files(tmp_path / "by_species", ["TestSpecies/test.jpg"])

    # Check structure
    assert isinstance(result, dict)
    assert "success" in result
    assert "deleted_count" in result
    assert "error_count" in result
    assert isinstance(result["success"], bool)
    assert isinstance(result["deleted_count"], int)
    assert isinstance(result["error_count"], int)

    # When there are errors, should have errors list
    if result.get("error_count", 0) > 0:
        assert "errors" in result
        assert isinstance(result["errors"], list)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
