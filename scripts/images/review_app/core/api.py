"""
Detection API wrapper with cache management.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import detection
from .storage import FAISSEmbeddingStore


class DetectionAPI:
    """
    Wrapper for detection functions with cache management.

    This class maintains hash and CNN caches for improved performance,
    and provides a clean interface for the HTTP handlers.
    """

    def __init__(self, faiss_store: Optional[FAISSEmbeddingStore] = None):
        """
        Initialize the detection API.

        Args:
            faiss_store: Optional FAISS embedding store for fast CNN similarity
        """
        self.hash_cache: Dict[str, Dict[Path, str]] = {}
        self.cnn_cache: Dict[str, Dict[Path, List[float]]] = {}
        self.faiss_store = faiss_store

    def get_species_list(self, base_dir: Path) -> List[str]:
        """Get list of species directories."""
        return detection.get_species_list(base_dir)

    def get_species_hashes(
        self, base_dir: Path, species_name: str, hash_size: int
    ) -> Dict[str, Any]:
        """Get image hashes for a species (without grouping)."""
        return detection.get_species_hashes(
            base_dir, species_name, hash_size, self.hash_cache
        )

    def get_species_duplicates(
        self, base_dir: Path, species_name: str, hash_size: int, hamming_threshold: int
    ) -> Dict[str, Any]:
        """Get duplicate groups for a species."""
        return detection.get_species_duplicates(
            base_dir, species_name, hash_size, hamming_threshold, self.hash_cache
        )

    def get_all_species_duplicates(
        self, base_dir: Path, hash_size: int, hamming_threshold: int
    ) -> Dict[str, Any]:
        """Get duplicate groups for ALL species."""
        return detection.get_all_species_duplicates(
            base_dir, hash_size, hamming_threshold, self.hash_cache
        )

    def get_species_cnn_similarity(
        self,
        base_dir: Path,
        species_name: str,
        similarity_threshold: float,
        model_name: str = detection.DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """Get CNN-based similar image groups for a species."""
        return detection.get_species_cnn_similarity(
            base_dir,
            species_name,
            similarity_threshold,
            model_name,
            self.cnn_cache,
            self.faiss_store,
        )

    def get_all_species_cnn_similarity(
        self,
        base_dir: Path,
        similarity_threshold: float,
        model_name: str = detection.DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """Get CNN-based similar groups across ALL species."""
        return detection.get_all_species_cnn_similarity(
            base_dir,
            similarity_threshold,
            model_name,
            self.cnn_cache,
            self.faiss_store,
        )

    def delete_files(self, base_dir: Path, file_paths: List[str]) -> Dict[str, Any]:
        """Delete the specified files and invalidate affected caches."""
        result = detection.delete_files(base_dir, file_paths)

        # Invalidate caches for affected species
        affected_species = result.get("affected_species", [])
        for species_name in affected_species:
            self.invalidate_species_cache(species_name)

        return result

    def invalidate_species_cache(self, species_name: str) -> None:
        """
        Invalidate all cache entries for a specific species.

        This should be called after files are deleted from a species directory
        to prevent stale cache data.
        """
        # Invalidate hash cache entries for this species
        keys_to_remove = [
            k for k in self.hash_cache if k.startswith(f"{species_name}_")
        ]
        for key in keys_to_remove:
            del self.hash_cache[key]

        # Invalidate CNN cache entries for this species
        keys_to_remove = [k for k in self.cnn_cache if k.startswith(f"{species_name}_")]
        for key in keys_to_remove:
            del self.cnn_cache[key]

    def clear_hash_cache(self) -> None:
        """Clear the hash cache."""
        self.hash_cache.clear()

    def clear_cnn_cache(self) -> None:
        """Clear the CNN cache."""
        self.cnn_cache.clear()

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.clear_hash_cache()
        self.clear_cnn_cache()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cache usage."""
        return {
            "hash_cache_entries": len(self.hash_cache),
            "cnn_cache_entries": len(self.cnn_cache),
        }
