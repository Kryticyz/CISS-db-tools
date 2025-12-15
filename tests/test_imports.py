"""
Test that all plantnet modules can be imported successfully.
"""

import pytest


def test_import_plantnet():
    """Test main package import."""
    import plantnet

    assert plantnet.__version__ == "1.0.0"


def test_import_core():
    """Test core module imports."""
    from plantnet.core import GBIFParser

    assert GBIFParser is not None


def test_import_utils():
    """Test utils module imports."""
    from plantnet.utils.paths import DATA_DIR, EMBEDDINGS_DIR, IMAGES_DIR

    assert DATA_DIR is not None
    assert IMAGES_DIR is not None
    assert EMBEDDINGS_DIR is not None


def test_import_images_deduplication():
    """Test deduplication module imports."""
    from plantnet.images.deduplication import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        DeduplicationResult,
        compute_image_hash,
        deduplicate_species_images,
    )

    assert deduplicate_species_images is not None
    assert DeduplicationResult is not None
    assert compute_image_hash is not None
    assert DEFAULT_HASH_SIZE == 16
    assert DEFAULT_HAMMING_THRESHOLD == 5


def test_import_images_similarity():
    """Test similarity module imports."""
    from plantnet.images.similarity import (
        DEFAULT_MODEL,
        DEFAULT_SIMILARITY_THRESHOLD,
        SimilarityResult,
        analyze_species_similarity,
        load_model,
    )

    assert analyze_species_similarity is not None
    assert SimilarityResult is not None
    assert load_model is not None
    assert DEFAULT_MODEL == "resnet18"
    assert DEFAULT_SIMILARITY_THRESHOLD == 0.85


def test_import_web():
    """Test web module imports."""
    from plantnet.web import main, run_server

    assert run_server is not None
    assert main is not None


def test_import_cli():
    """Test CLI module imports."""
    from plantnet.cli import main as cli_main
    from plantnet.cli.analysis_cmds import analyze_cli
    from plantnet.cli.database_cmds import build_cli, query_cli
    from plantnet.cli.image_cmds import deduplicate_cli, embeddings_cli

    assert cli_main is not None
    assert deduplicate_cli is not None
    assert embeddings_cli is not None
    assert query_cli is not None
    assert build_cli is not None
    assert analyze_cli is not None
