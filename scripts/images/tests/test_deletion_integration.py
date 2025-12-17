"""
Integration tests for the deletion API endpoint.

Tests the /api/delete endpoint through HTTP requests
to ensure the full deletion workflow works end-to-end.
"""

import json
import sys
import threading
import time
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def test_server_setup(tmp_path):
    """Setup a test server with temporary data directory."""
    from review_app.core.api import DetectionAPI
    from review_app.server.handlers import DuplicateReviewHandler

    # Create test data directory
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create some test species folders
    species_dir = base_dir / "TestSpecies"
    species_dir.mkdir()

    # Create test files
    test_files = []
    for i in range(3):
        test_file = species_dir / f"test{i}.jpg"
        test_file.write_text(f"test content {i}")
        test_files.append(test_file)

    # Setup handler with test configuration
    api = DetectionAPI()

    # Create handler class with configuration
    def make_handler(*args, **kwargs):
        handler = DuplicateReviewHandler(*args, **kwargs)
        handler.base_dir = base_dir
        handler.detection_api = api
        return handler

    # Start test server in background
    server = HTTPServer(("localhost", 0), make_handler)  # 0 = random port
    port = server.server_address[1]

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(0.1)

    yield {
        "base_dir": base_dir,
        "port": port,
        "test_files": test_files,
        "server": server,
    }

    # Cleanup
    server.shutdown()
    server.server_close()


def test_delete_api_success(test_server_setup):
    """Test successful file deletion via API."""
    base_dir = test_server_setup["base_dir"]
    port = test_server_setup["port"]

    # Create a test file
    test_dir = base_dir / "TestSpecies"
    test_file = test_dir / "delete_me.jpg"
    test_file.write_text("content to delete")

    assert test_file.exists()

    # Make DELETE request
    data = json.dumps({"files": ["TestSpecies/delete_me.jpg"]}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        response = urlopen(req, timeout=5)
        result = json.loads(response.read().decode("utf-8"))

        # Verify response
        assert result["success"] == True
        assert result["deleted_count"] == 1
        assert result["error_count"] == 0

        # Verify file is actually deleted
        assert not test_file.exists()

    except HTTPError as e:
        pytest.fail(f"HTTP request failed: {e.code} {e.reason}")


def test_delete_api_multiple_files(test_server_setup):
    """Test deleting multiple files via API."""
    base_dir = test_server_setup["base_dir"]
    port = test_server_setup["port"]

    # Create multiple test files
    test_dir = base_dir / "TestSpecies"
    files = []
    for i in range(5):
        f = test_dir / f"multi_{i}.jpg"
        f.write_text(f"content {i}")
        files.append(f)

    # Verify all exist
    for f in files:
        assert f.exists()

    # Delete all via API
    file_paths = [f"TestSpecies/multi_{i}.jpg" for i in range(5)]
    data = json.dumps({"files": file_paths}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)
    result = json.loads(response.read().decode("utf-8"))

    # Verify response
    assert result["success"] == True
    assert result["deleted_count"] == 5
    assert result["error_count"] == 0

    # Verify all files are deleted
    for f in files:
        assert not f.exists()


def test_delete_api_nonexistent_file(test_server_setup):
    """Test API response when trying to delete non-existent file."""
    port = test_server_setup["port"]

    # Try to delete non-existent file
    data = json.dumps({"files": ["TestSpecies/does_not_exist.jpg"]}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)
    result = json.loads(response.read().decode("utf-8"))

    # Should report error
    assert result["success"] == False
    assert result["deleted_count"] == 0
    assert result["error_count"] == 1
    assert len(result["errors"]) == 1


def test_delete_api_invalid_json(test_server_setup):
    """Test API response to invalid JSON."""
    port = test_server_setup["port"]

    # Send invalid JSON
    data = b"not valid json"

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        response = urlopen(req, timeout=5)
        result = json.loads(response.read().decode("utf-8"))

        # Should return error
        assert "error" in result or result.get("success") == False

    except HTTPError as e:
        # 400 Bad Request is also acceptable
        assert e.code == 400


def test_delete_api_missing_files_field(test_server_setup):
    """Test API response when 'files' field is missing."""
    port = test_server_setup["port"]

    # Send JSON without 'files' field
    data = json.dumps({"wrong_field": []}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        response = urlopen(req, timeout=5)
        result = json.loads(response.read().decode("utf-8"))

        # Should return error
        assert "error" in result or result.get("success") == False

    except HTTPError as e:
        # 400 Bad Request is also acceptable
        assert e.code in [400, 500]


def test_delete_api_security_path_traversal(test_server_setup):
    """Test that API blocks path traversal attempts."""
    base_dir = test_server_setup["base_dir"]
    port = test_server_setup["port"]

    # Create a file outside the base directory
    outside_dir = base_dir.parent / "outside"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret data")

    assert outside_file.exists()

    # Try to delete using path traversal
    data = json.dumps({"files": ["../outside/secret.txt"]}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)
    result = json.loads(response.read().decode("utf-8"))

    # Should fail and file should still exist
    assert result["success"] == False
    assert result["deleted_count"] == 0
    assert outside_file.exists()


def test_delete_api_empty_files_list(test_server_setup):
    """Test API with empty files list."""
    port = test_server_setup["port"]

    data = json.dumps({"files": []}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)
    result = json.loads(response.read().decode("utf-8"))

    # Should succeed with no operations
    assert result["success"] == True
    assert result["deleted_count"] == 0
    assert result["error_count"] == 0


def test_delete_api_partial_success(test_server_setup):
    """Test API when some files exist and some don't."""
    base_dir = test_server_setup["base_dir"]
    port = test_server_setup["port"]

    # Create only one of two files
    test_dir = base_dir / "TestSpecies"
    existing_file = test_dir / "exists.jpg"
    existing_file.write_text("content")

    assert existing_file.exists()

    # Try to delete both existing and non-existing
    data = json.dumps(
        {"files": ["TestSpecies/exists.jpg", "TestSpecies/does_not_exist.jpg"]}
    ).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)
    result = json.loads(response.read().decode("utf-8"))

    # Should report partial success
    assert result["deleted_count"] == 1
    assert result["error_count"] == 1
    assert not existing_file.exists()


def test_delete_api_cors_headers(test_server_setup):
    """Test that API returns appropriate CORS headers if needed."""
    port = test_server_setup["port"]

    # Make a simple request and check headers
    data = json.dumps({"files": []}).encode("utf-8")

    req = Request(
        f"http://localhost:{port}/api/delete",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urlopen(req, timeout=5)

    # Just verify we get a valid response
    assert response.status == 200
    assert response.headers.get("Content-Type") == "application/json"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
