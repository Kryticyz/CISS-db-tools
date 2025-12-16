"""
Detection service wrapping the existing DetectionAPI.

Provides a thin wrapper around the existing core detection modules
with type-safe return values matching our Pydantic models.
"""

import sys
from pathlib import Path
from typing import Any, Optional

# Add paths for imports
_package_dir = Path(__file__).parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))
_scripts_images_dir = _package_dir.parent
if str(_scripts_images_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_images_dir))

from review_app.core.api import DetectionAPI
from review_app.core.storage import FAISSEmbeddingStore, init_faiss_store

from models.analysis import (
    DuplicateGroup,
    DuplicateResult,
    ImageInfo,
    SimilarGroup,
    SimilarityResult,
)
from models.species import SpeciesInfo


class DetectionService:
    """
    Service for duplicate and similarity detection.

    Wraps the existing DetectionAPI with type-safe interfaces.
    """

    def __init__(
        self,
        base_dir: Path,
        faiss_store: Optional[FAISSEmbeddingStore] = None,
    ):
        """
        Initialize detection service.

        Args:
            base_dir: Base directory containing species folders
            faiss_store: Optional pre-loaded FAISS store
        """
        self.base_dir = base_dir
        self.faiss_store = faiss_store
        self._api = DetectionAPI(faiss_store=faiss_store)

    def get_species_list(self) -> list[str]:
        """Get list of species with images."""
        return self._api.get_species_list(self.base_dir)

    def get_species_info(self, species_name: str) -> Optional[SpeciesInfo]:
        """Get information about a species."""
        species_dir = self.base_dir / species_name
        if not species_dir.exists() or not species_dir.is_dir():
            return None

        # Count images
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        image_count = sum(
            1
            for f in species_dir.iterdir()
            if f.suffix.lower() in image_extensions
        )

        # Check if species has embeddings
        has_embeddings = False
        if self.faiss_store is not None:
            species_in_faiss = {m["species"] for m in self.faiss_store.metadata}
            has_embeddings = species_name in species_in_faiss

        return SpeciesInfo(
            name=species_name,
            image_count=image_count,
            has_embeddings=has_embeddings,
        )

    def get_duplicates(
        self,
        species_name: str,
        hash_size: int = 16,
        hamming_threshold: int = 5,
    ) -> DuplicateResult:
        """
        Detect duplicate images using perceptual hashing.

        Args:
            species_name: Species to analyze
            hash_size: Hash precision (8-32)
            hamming_threshold: Maximum hash difference for duplicates

        Returns:
            DuplicateResult with grouped duplicates
        """
        result = self._api.get_species_duplicates(
            self.base_dir, species_name, hash_size, hamming_threshold
        )

        if "error" in result:
            return DuplicateResult(
                species_name=species_name,
                total_images=0,
                hashed_images=0,
                duplicate_groups=[],
                total_duplicates=0,
                hash_size=hash_size,
                hamming_threshold=hamming_threshold,
            )

        # Convert to typed models
        groups = []
        for g in result.get("duplicate_groups", []):
            keep = g.get("keep", {})
            groups.append(
                DuplicateGroup(
                    group_id=g["group_id"],
                    keep=ImageInfo(
                        filename=keep.get("filename", ""),
                        path=keep.get("path", ""),
                        size=keep.get("size", 0),
                        hash=keep.get("hash"),
                    ),
                    duplicates=[
                        ImageInfo(
                            filename=d.get("filename", ""),
                            path=d.get("path", ""),
                            size=d.get("size", 0),
                            hash=d.get("hash"),
                        )
                        for d in g.get("duplicates", [])
                    ],
                    total_in_group=g.get("total_in_group", 0),
                )
            )

        return DuplicateResult(
            species_name=species_name,
            total_images=result.get("total_images", 0),
            hashed_images=result.get("hashed_images", 0),
            duplicate_groups=groups,
            total_duplicates=result.get("total_duplicates", 0),
            hash_size=hash_size,
            hamming_threshold=hamming_threshold,
        )

    def get_similarity(
        self,
        species_name: str,
        similarity_threshold: float = 0.85,
        model_name: str = "resnet18",
    ) -> SimilarityResult:
        """
        Detect similar images using CNN embeddings.

        Args:
            species_name: Species to analyze
            similarity_threshold: Minimum cosine similarity (0.5-1.0)
            model_name: CNN model name

        Returns:
            SimilarityResult with grouped similar images
        """
        result = self._api.get_species_cnn_similarity(
            self.base_dir, species_name, similarity_threshold, model_name
        )

        if "error" in result:
            return SimilarityResult(
                species_name=species_name,
                total_images=0,
                processed_images=0,
                similar_groups=[],
                total_in_groups=0,
                similarity_threshold=similarity_threshold,
                model_name=model_name,
                from_faiss=False,
            )

        # Convert to typed models
        groups = []
        for g in result.get("similar_groups", []):
            groups.append(
                SimilarGroup(
                    group_id=g.get("group_id", 0),
                    images=[
                        ImageInfo(
                            filename=img.get("filename", ""),
                            path=img.get("path", ""),
                            size=img.get("size", 0),
                        )
                        for img in g.get("images", [])
                    ],
                    count=g.get("count", 0),
                )
            )

        return SimilarityResult(
            species_name=species_name,
            total_images=result.get("total_images", 0),
            processed_images=result.get("processed_images", 0),
            similar_groups=groups,
            total_in_groups=result.get("total_in_groups", 0),
            similarity_threshold=similarity_threshold,
            model_name=result.get("model_name", model_name),
            from_faiss=result.get("from_faiss", False),
        )

    def invalidate_cache(self, species_name: str) -> None:
        """Invalidate cached data for a species after deletion."""
        self._api.invalidate_species_cache(species_name)

    def clear_all_caches(self) -> None:
        """Clear all cached data."""
        self._api.clear_all_caches()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return self._api.get_cache_stats()


def create_detection_service(
    base_dir: Path,
    embeddings_dir: Optional[Path] = None,
) -> DetectionService:
    """
    Factory function to create a DetectionService with FAISS support.

    Args:
        base_dir: Base directory containing species folders
        embeddings_dir: Directory containing FAISS embeddings

    Returns:
        Configured DetectionService instance
    """
    faiss_store = None
    if embeddings_dir is not None and embeddings_dir.exists():
        faiss_store = init_faiss_store(embeddings_dir)

    return DetectionService(base_dir, faiss_store)
