"""
Pytest configuration and fixtures for plantnet tests.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_species_dir(temp_dir):
    """Create a sample species directory structure."""
    species_dir = temp_dir / "Acacia_dealbata"
    species_dir.mkdir(parents=True, exist_ok=True)
    return species_dir
