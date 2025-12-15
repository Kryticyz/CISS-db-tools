"""
PlantNet Image Mining Toolkit

A comprehensive toolkit for mining, analyzing, and managing plant species
images from PlantNet via GBIF data exports.
"""

__version__ = "1.0.0"
__author__ = "Tynan Matthews"
__email__ = "tynan@matthews.solutions"

# Import core modules
from plantnet.core import GBIFParser
from plantnet.images import (
    DeduplicationResult,
    SimilarityResult,
    analyze_species_similarity,
    deduplicate_species_images,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "GBIFParser",
    "deduplicate_species_images",
    "DeduplicationResult",
    "analyze_species_similarity",
    "SimilarityResult",
]
