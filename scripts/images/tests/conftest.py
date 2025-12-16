"""
Pytest configuration and shared fixtures for the test suite.

This file provides common test fixtures and configuration
that can be used across all test modules.
"""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_base_dir(tmp_path):
    """
    Create a temporary base directory with species structure.

    Returns a Path object to a temporary directory containing:
    - by_species/
      - Species1/
      - Species2/
      - Species3/
    """
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    # Create some species folders
    for i in range(1, 4):
        species_dir = base_dir / f"Species{i}"
        species_dir.mkdir()

    return base_dir


@pytest.fixture
def sample_images(temp_base_dir):
    """
    Create sample image files in the test directory.

    Returns a dict mapping species names to lists of file paths.
    """
    images = {}

    for species_dir in temp_base_dir.iterdir():
        if species_dir.is_dir():
            species_name = species_dir.name
            species_images = []

            # Create 5 sample images per species
            for i in range(5):
                img_file = species_dir / f"image_{i:03d}.jpg"
                img_file.write_bytes(b"fake image data " * (i + 1))  # Varying sizes
                species_images.append(img_file)

            images[species_name] = species_images

    return images


@pytest.fixture
def detection_api():
    """
    Create a DetectionAPI instance for testing.
    """
    from review_app.core.api import DetectionAPI

    return DetectionAPI()


@pytest.fixture
def mock_faiss_store(tmp_path):
    """
    Create a mock FAISS store for testing CNN similarity.

    Note: This is a minimal mock. For real FAISS tests,
    you would need actual embedding files.
    """
    embeddings_dir = tmp_path / "embeddings"
    embeddings_dir.mkdir()

    # In a real scenario, you would create actual FAISS index files here
    # For now, this is just a placeholder

    return embeddings_dir


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Automatically cleanup after each test.

    This fixture runs automatically after every test.
    """
    yield
    # Cleanup code here if needed


def pytest_configure(config):
    """
    Pytest configuration hook.

    This is called before test collection begins.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture
def mock_request_handler():
    """
    Create a mock HTTP request handler for testing endpoints.
    """
    from http.server import BaseHTTPRequestHandler
    from io import BytesIO

    class MockRequest:
        def __init__(self, method="GET", path="/", body=b""):
            self.method = method
            self.path = path
            self.body = body
            self._rfile = BytesIO(body)
            self._wfile = BytesIO()

        def makefile(self, mode):
            if "r" in mode:
                return self._rfile
            elif "w" in mode:
                return self._wfile

    return MockRequest


# Test data constants
TEST_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
TEST_HASH_SIZE = 16
TEST_HAMMING_THRESHOLD = 5
TEST_CNN_THRESHOLD = 0.85


# Helper functions for tests
def create_test_image_file(path: Path, size_kb: int = 1):
    """
    Create a fake image file for testing.

    Args:
        path: Path where to create the file
        size_kb: Approximate size in KB
    """
    content = b"fake image data " * (size_kb * 64)  # Rough approximation
    path.write_bytes(content)


def create_species_structure(base_dir: Path, species_list: list):
    """
    Create a species folder structure for testing.

    Args:
        base_dir: Base directory to create structure in
        species_list: List of species names
    """
    for species in species_list:
        species_dir = base_dir / species
        species_dir.mkdir(exist_ok=True)
