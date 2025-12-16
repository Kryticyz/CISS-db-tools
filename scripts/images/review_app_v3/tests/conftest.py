"""
Test fixtures for the review application.
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Add parent path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import create_app
from config import init_settings
from services.deletion_queue import DeletionQueueService
from models.deletion import DeletionReason


@pytest.fixture
def temp_species_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with mock species folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create mock species directories with images
        for species in ["Test_Species_A", "Test_Species_B"]:
            species_dir = base_dir / species
            species_dir.mkdir()

            # Create mock image files
            for i in range(5):
                img_path = species_dir / f"image_{i}.jpg"
                img_path.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)  # Fake JPEG header

        yield base_dir


@pytest.fixture
def temp_embeddings_dir() -> Generator[Path, None, None]:
    """Create a temporary embeddings directory (empty for now)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def deletion_queue(temp_species_dir: Path) -> DeletionQueueService:
    """Create a deletion queue service for testing."""
    return DeletionQueueService(temp_species_dir)


@pytest.fixture
def test_client(temp_species_dir: Path, temp_embeddings_dir: Path) -> Generator[TestClient, None, None]:
    """Create a test client with mock directories."""
    # Initialize settings with temp directories
    init_settings(
        base_dir=temp_species_dir,
        embeddings_dir=temp_embeddings_dir,
        require_embeddings=False,  # Don't require embeddings for tests
    )

    # Create app
    app = create_app(
        base_dir=temp_species_dir,
        embeddings_dir=temp_embeddings_dir,
    )

    with TestClient(app) as client:
        yield client
