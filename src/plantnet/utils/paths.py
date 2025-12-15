"""Centralized path configuration for plantnet.

This module provides consistent path references across the package,
with support for environment variable overrides.
"""

import os
from pathlib import Path

# Project root is four levels up from this file (src/plantnet/utils/paths.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Data directories (default locations)
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASES_DIR = DATA_DIR / "databases"
IMAGES_DIR = DATA_DIR / "images"
REPORTS_DIR = DATA_DIR / "reports"

# GBIF data
GBIF_RAW_DIR = RAW_DIR / "gbif"
GBIF_MULTIMEDIA_FILE = GBIF_RAW_DIR / "multimedia.txt"
GBIF_OCCURRENCE_FILE = GBIF_RAW_DIR / "occurrence.txt"

# Databases
GBIF_DB = DATABASES_DIR / "plantnet_gbif.db"
COUNTS_DB = DATABASES_DIR / "plantnet_counts.db"
EMBEDDINGS_DIR = DATABASES_DIR / "embeddings"

# Images
IMAGES_BY_SPECIES = IMAGES_DIR / "by_species"
IMAGES_UNCATEGORIZED = IMAGES_DIR / "uncategorized"

# Processed data
SPECIES_URLS_DIR = PROCESSED_DIR / "species_urls"
SYNONYMS_DIR = PROCESSED_DIR / "synonyms"
COUNTS_DIR = PROCESSED_DIR / "counts"


def get_data_dir() -> Path:
    """Get data directory, respecting PLANTNET_DATA_DIR env var.

    Returns:
        Path: Data directory path

    Examples:
        >>> # Use default
        >>> data_dir = get_data_dir()

        >>> # Override via environment variable
        >>> import os
        >>> os.environ['PLANTNET_DATA_DIR'] = '/path/to/data'
        >>> data_dir = get_data_dir()
    """
    custom_dir = os.environ.get("PLANTNET_DATA_DIR")
    if custom_dir:
        return Path(custom_dir)
    return DATA_DIR


def get_species_image_dir(species_name: str) -> Path:
    """Get the directory for a specific species' images.

    Args:
        species_name: Species name in Genus_species format

    Returns:
        Path: Directory path for species images

    Examples:
        >>> dir_path = get_species_image_dir("Acacia_dealbata")
        >>> print(dir_path)
        .../data/images/by_species/Acacia_dealbata
    """
    return IMAGES_BY_SPECIES / species_name


def get_species_urls_file(species_name: str) -> Path:
    """Get the URL file for a specific species.

    Args:
        species_name: Species name in Genus_species format

    Returns:
        Path: File path for species URLs

    Examples:
        >>> file_path = get_species_urls_file("Acacia_dealbata")
        >>> print(file_path)
        .../data/processed/species_urls/Acacia_dealbata_urls.txt
    """
    return SPECIES_URLS_DIR / f"{species_name}_urls.txt"


__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DIR",
    "PROCESSED_DIR",
    "DATABASES_DIR",
    "IMAGES_DIR",
    "REPORTS_DIR",
    "GBIF_RAW_DIR",
    "GBIF_MULTIMEDIA_FILE",
    "GBIF_OCCURRENCE_FILE",
    "GBIF_DB",
    "COUNTS_DB",
    "EMBEDDINGS_DIR",
    "IMAGES_BY_SPECIES",
    "IMAGES_UNCATEGORIZED",
    "SPECIES_URLS_DIR",
    "SYNONYMS_DIR",
    "COUNTS_DIR",
    "get_data_dir",
    "get_species_image_dir",
    "get_species_urls_file",
]
