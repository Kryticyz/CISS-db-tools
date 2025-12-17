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


def create_valid_test_image(
    path: Path, width: int = 10, height: int = 10, color: tuple = (255, 0, 0)
):
    """
    Create a valid image file that can be processed by image hashing libraries.

    Args:
        path: Path where to create the image
        width: Image width in pixels
        height: Image height in pixels
        color: RGB color tuple for the image
    """
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), color)
        img.save(path)
    except ImportError:
        # Fallback: create a minimal valid JPEG header
        # This is a 1x1 red JPEG
        jpeg_data = bytes(
            [
                0xFF,
                0xD8,
                0xFF,
                0xE0,
                0x00,
                0x10,
                0x4A,
                0x46,
                0x49,
                0x46,
                0x00,
                0x01,
                0x01,
                0x00,
                0x00,
                0x01,
                0x00,
                0x01,
                0x00,
                0x00,
                0xFF,
                0xDB,
                0x00,
                0x43,
                0x00,
                0x08,
                0x06,
                0x06,
                0x07,
                0x06,
                0x05,
                0x08,
                0x07,
                0x07,
                0x07,
                0x09,
                0x09,
                0x08,
                0x0A,
                0x0C,
                0x14,
                0x0D,
                0x0C,
                0x0B,
                0x0B,
                0x0C,
                0x19,
                0x12,
                0x13,
                0x0F,
                0x14,
                0x1D,
                0x1A,
                0x1F,
                0x1E,
                0x1D,
                0x1A,
                0x1C,
                0x1C,
                0x20,
                0x24,
                0x2E,
                0x27,
                0x20,
                0x22,
                0x2C,
                0x23,
                0x1C,
                0x1C,
                0x28,
                0x37,
                0x29,
                0x2C,
                0x30,
                0x31,
                0x34,
                0x34,
                0x34,
                0x1F,
                0x27,
                0x39,
                0x3D,
                0x38,
                0x32,
                0x3C,
                0x2E,
                0x33,
                0x34,
                0x32,
                0xFF,
                0xC0,
                0x00,
                0x0B,
                0x08,
                0x00,
                0x01,
                0x00,
                0x01,
                0x01,
                0x01,
                0x11,
                0x00,
                0xFF,
                0xC4,
                0x00,
                0x1F,
                0x00,
                0x00,
                0x01,
                0x05,
                0x01,
                0x01,
                0x01,
                0x01,
                0x01,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x01,
                0x02,
                0x03,
                0x04,
                0x05,
                0x06,
                0x07,
                0x08,
                0x09,
                0x0A,
                0x0B,
                0xFF,
                0xC4,
                0x00,
                0xB5,
                0x10,
                0x00,
                0x02,
                0x01,
                0x03,
                0x03,
                0x02,
                0x04,
                0x03,
                0x05,
                0x05,
                0x04,
                0x04,
                0x00,
                0x00,
                0x01,
                0x7D,
                0x01,
                0x02,
                0x03,
                0x00,
                0x04,
                0x11,
                0x05,
                0x12,
                0x21,
                0x31,
                0x41,
                0x06,
                0x13,
                0x51,
                0x61,
                0x07,
                0x22,
                0x71,
                0x14,
                0x32,
                0x81,
                0x91,
                0xA1,
                0x08,
                0x23,
                0x42,
                0xB1,
                0xC1,
                0x15,
                0x52,
                0xD1,
                0xF0,
                0x24,
                0x33,
                0x62,
                0x72,
                0x82,
                0x09,
                0x0A,
                0x16,
                0x17,
                0x18,
                0x19,
                0x1A,
                0x25,
                0x26,
                0x27,
                0x28,
                0x29,
                0x2A,
                0x34,
                0x35,
                0x36,
                0x37,
                0x38,
                0x39,
                0x3A,
                0x43,
                0x44,
                0x45,
                0x46,
                0x47,
                0x48,
                0x49,
                0x4A,
                0x53,
                0x54,
                0x55,
                0x56,
                0x57,
                0x58,
                0x59,
                0x5A,
                0x63,
                0x64,
                0x65,
                0x66,
                0x67,
                0x68,
                0x69,
                0x6A,
                0x73,
                0x74,
                0x75,
                0x76,
                0x77,
                0x78,
                0x79,
                0x7A,
                0x83,
                0x84,
                0x85,
                0x86,
                0x87,
                0x88,
                0x89,
                0x8A,
                0x92,
                0x93,
                0x94,
                0x95,
                0x96,
                0x97,
                0x98,
                0x99,
                0x9A,
                0xA2,
                0xA3,
                0xA4,
                0xA5,
                0xA6,
                0xA7,
                0xA8,
                0xA9,
                0xAA,
                0xB2,
                0xB3,
                0xB4,
                0xB5,
                0xB6,
                0xB7,
                0xB8,
                0xB9,
                0xBA,
                0xC2,
                0xC3,
                0xC4,
                0xC5,
                0xC6,
                0xC7,
                0xC8,
                0xC9,
                0xCA,
                0xD2,
                0xD3,
                0xD4,
                0xD5,
                0xD6,
                0xD7,
                0xD8,
                0xD9,
                0xDA,
                0xE1,
                0xE2,
                0xE3,
                0xE4,
                0xE5,
                0xE6,
                0xE7,
                0xE8,
                0xE9,
                0xEA,
                0xF1,
                0xF2,
                0xF3,
                0xF4,
                0xF5,
                0xF6,
                0xF7,
                0xF8,
                0xF9,
                0xFA,
                0xFF,
                0xDA,
                0x00,
                0x08,
                0x01,
                0x01,
                0x00,
                0x00,
                0x3F,
                0x00,
                0xFB,
                0xD5,
                0xDB,
                0x20,
                0xA8,
                0xF1,
                0x7E,
                0xA5,
                0xFF,
                0xD9,
            ]
        )
        path.write_bytes(jpeg_data)


@pytest.fixture
def species_with_valid_images(tmp_path):
    """
    Create species directories with valid image files that can be hashed.

    Returns a tuple of (base_dir, images_dict) where images_dict maps
    species names to lists of image file paths.
    """
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    images = {}

    # Create Species1 with 3 images
    species1_dir = base_dir / "Species1"
    species1_dir.mkdir()
    species1_images = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        img_path = species1_dir / f"image_{i:03d}.jpg"
        create_valid_test_image(
            img_path, width=50 + i * 10, height=50 + i * 10, color=color
        )
        species1_images.append(img_path)
    images["Species1"] = species1_images

    # Create Species2 with 3 images
    species2_dir = base_dir / "Species2"
    species2_dir.mkdir()
    species2_images = []
    for i, color in enumerate([(128, 128, 0), (0, 128, 128), (128, 0, 128)]):
        img_path = species2_dir / f"image_{i:03d}.jpg"
        create_valid_test_image(
            img_path, width=60 + i * 10, height=60 + i * 10, color=color
        )
        species2_images.append(img_path)
    images["Species2"] = species2_images

    return base_dir, images


@pytest.fixture
def species_with_duplicate_images(tmp_path):
    """
    Create species directories with duplicate image files (identical content).

    Returns a tuple of (base_dir, images_dict, duplicates_info) where:
    - images_dict maps species names to lists of image file paths
    - duplicates_info contains info about which images are duplicates
    """
    base_dir = tmp_path / "by_species"
    base_dir.mkdir()

    images = {}
    duplicates_info = {}

    # Create Species1 with duplicates (same color = same hash)
    species1_dir = base_dir / "Species1"
    species1_dir.mkdir()
    species1_images = []

    # Create 2 identical images (duplicates) and 1 unique
    create_valid_test_image(
        species1_dir / "original.jpg", width=100, height=100, color=(255, 0, 0)
    )
    create_valid_test_image(
        species1_dir / "duplicate1.jpg", width=100, height=100, color=(255, 0, 0)
    )
    create_valid_test_image(
        species1_dir / "unique.jpg", width=100, height=100, color=(0, 255, 0)
    )

    species1_images = [
        species1_dir / "original.jpg",
        species1_dir / "duplicate1.jpg",
        species1_dir / "unique.jpg",
    ]
    images["Species1"] = species1_images
    duplicates_info["Species1"] = {
        "duplicate_group": ["original.jpg", "duplicate1.jpg"],
        "unique": ["unique.jpg"],
    }

    return base_dir, images, duplicates_info


@pytest.fixture
def populated_detection_api(species_with_valid_images):
    """
    Create a DetectionAPI instance with pre-populated caches.
    """
    from review_app.core.api import DetectionAPI

    base_dir, images = species_with_valid_images
    api = DetectionAPI()

    # Populate hash cache by calling get_species_hashes
    for species_name in images.keys():
        api.get_species_hashes(base_dir, species_name, TEST_HASH_SIZE)

    return api, base_dir, images


@pytest.fixture
def mock_faiss_store_with_data():
    """
    Create a mock FAISSEmbeddingStore that returns predictable results.
    """

    class MockFAISSStore:
        def __init__(self):
            self.search_called = False
            self.last_species = None
            self.last_threshold = None

        def search_species(self, species_name: str, threshold: float = 0.85):
            self.search_called = True
            self.last_species = species_name
            self.last_threshold = threshold
            # Return mock similar groups
            return [
                {
                    "group_id": 1,
                    "images": [
                        {
                            "filename": "img1.jpg",
                            "size": 1000,
                            "path": f"/image/{species_name}/img1.jpg",
                        },
                        {
                            "filename": "img2.jpg",
                            "size": 900,
                            "path": f"/image/{species_name}/img2.jpg",
                        },
                    ],
                    "count": 2,
                }
            ]

        def get_status(self):
            return {"available": True, "count": 100, "location": "/mock/path"}

    return MockFAISSStore()


@pytest.fixture
def mock_faiss_store_raises():
    """
    Create a mock FAISSEmbeddingStore that raises an exception on search.
    """

    class MockFAISSStoreError:
        def search_species(self, species_name: str, threshold: float = 0.85):
            raise RuntimeError("FAISS search failed")

        def get_status(self):
            return {"available": False, "count": 0, "location": None}

    return MockFAISSStoreError()
