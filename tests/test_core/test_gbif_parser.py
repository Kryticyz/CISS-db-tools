"""
Tests for GBIF Parser module.
"""

from pathlib import Path

import pytest

from plantnet.core.gbif_parser import GBIFParser


def test_gbif_parser_instantiation():
    """Test that GBIFParser can be instantiated."""
    parser = GBIFParser()
    assert parser is not None
    assert parser.gbif_dir is not None


def test_gbif_parser_custom_directory():
    """Test GBIFParser with custom directory."""
    custom_dir = Path("/tmp/test_gbif")
    parser = GBIFParser(gbif_dir=custom_dir)
    assert parser.gbif_dir == custom_dir


def test_gbif_parser_has_expected_methods():
    """Test that GBIFParser has expected methods."""
    parser = GBIFParser()
    assert hasattr(parser, "load_all")
    assert callable(parser.load_all)
    # Check for data attributes
    assert hasattr(parser, "occurrence_data")
    assert hasattr(parser, "multimedia_data")
    assert hasattr(parser, "loaded")
