"""
Core detection and storage logic.
"""

from .api import DetectionAPI
from .detection import (
    CNN_AVAILABLE,
    DEFAULT_HAMMING_THRESHOLD,
    DEFAULT_HASH_SIZE,
    DEFAULT_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    delete_files,
    get_all_species_duplicates,
    get_species_cnn_similarity,
    get_species_duplicates,
    get_species_hashes,
    get_species_list,
)
from .storage import FAISSEmbeddingStore, init_faiss_store

__all__ = [
    "DetectionAPI",
    "FAISSEmbeddingStore",
    "init_faiss_store",
    "CNN_AVAILABLE",
    "DEFAULT_HAMMING_THRESHOLD",
    "DEFAULT_HASH_SIZE",
    "DEFAULT_MODEL",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "delete_files",
    "get_all_species_duplicates",
    "get_species_cnn_similarity",
    "get_species_duplicates",
    "get_species_hashes",
    "get_species_list",
]
