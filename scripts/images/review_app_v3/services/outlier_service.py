"""
Outlier detection service using centroid distance.

Adapted from scripts/images/detect_outliers.py for the web interface.
Uses pre-computed species statistics for fast outlier detection.
"""

import json
import pickle
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Add paths for imports
_package_dir = Path(__file__).parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from models.analysis import OutlierInfo, OutlierResult


class OutlierService:
    """
    Service for centroid-based outlier detection.

    Uses pre-computed species centroids to identify images
    that are unusually far from their species cluster.
    """

    def __init__(self, embeddings_dir: Path):
        """
        Initialize outlier service.

        Args:
            embeddings_dir: Directory containing FAISS embeddings and stats
        """
        self.embeddings_dir = embeddings_dir
        self._metadata: Optional[list[dict]] = None
        self._species_stats: Optional[dict] = None

    @property
    def metadata(self) -> list[dict]:
        """Lazy-load full metadata with embeddings."""
        if self._metadata is None:
            metadata_path = self.embeddings_dir / "metadata_full.pkl"
            if not metadata_path.exists():
                raise FileNotFoundError(
                    f"metadata_full.pkl not found in {self.embeddings_dir}"
                )
            with open(metadata_path, "rb") as f:
                self._metadata = pickle.load(f)
        return self._metadata

    @property
    def species_stats(self) -> dict:
        """Lazy-load species statistics (centroids, distances)."""
        if self._species_stats is None:
            stats_path = self.embeddings_dir / "species_stats.json"
            if not stats_path.exists():
                raise FileNotFoundError(
                    f"species_stats.json not found in {self.embeddings_dir}"
                )
            with open(stats_path, "r") as f:
                self._species_stats = json.load(f)
        return self._species_stats

    def get_available_species(self) -> list[str]:
        """Get list of species with outlier detection available."""
        return list(self.species_stats.keys())

    def has_species(self, species_name: str) -> bool:
        """Check if species has data for outlier detection."""
        return species_name in self.species_stats

    def detect_outliers(
        self,
        species_name: str,
        threshold_percentile: float = 95.0,
    ) -> OutlierResult:
        """
        Detect outliers for a species using centroid distance.

        Images with distance from the species centroid above the
        specified percentile are flagged as outliers.

        Args:
            species_name: Species to analyze
            threshold_percentile: Percentile above which images are outliers

        Returns:
            OutlierResult with detected outliers
        """
        if species_name not in self.species_stats:
            return OutlierResult(
                species_name=species_name,
                total_images=0,
                outliers=[],
                outlier_count=0,
                threshold_percentile=threshold_percentile,
                computed_threshold=0.0,
                mean_distance=0.0,
                std_distance=0.0,
            )

        # Get species-specific data
        stats = self.species_stats[species_name]
        species_metadata = [m for m in self.metadata if m["species"] == species_name]

        if len(species_metadata) < 3:
            return OutlierResult(
                species_name=species_name,
                total_images=len(species_metadata),
                outliers=[],
                outlier_count=0,
                threshold_percentile=threshold_percentile,
                computed_threshold=0.0,
                mean_distance=stats.get("mean_distance", 0.0),
                std_distance=stats.get("std_distance", 0.0),
            )

        # Get centroid from pre-computed stats
        centroid = np.array(stats["centroid"], dtype=np.float32)

        # Compute distances for all images
        distances = []
        for m in species_metadata:
            emb = np.array(m["embedding"], dtype=np.float32)
            # Normalize for cosine similarity
            emb_norm = emb / np.linalg.norm(emb)
            # Cosine distance = 1 - cosine similarity
            distance = 1.0 - float(np.dot(emb_norm, centroid))
            distances.append(distance)

        distances = np.array(distances)
        threshold = float(np.percentile(distances, threshold_percentile))

        # Compute z-scores
        mean_dist = float(np.mean(distances))
        std_dist = float(np.std(distances))

        # Find outliers
        outliers = []
        for idx, (m, dist) in enumerate(zip(species_metadata, distances)):
            if dist > threshold:
                z_score = (dist - mean_dist) / std_dist if std_dist > 0 else 0.0
                outliers.append(
                    OutlierInfo(
                        filename=m["filename"],
                        path=f"/api/images/{species_name}/{m['filename']}",
                        size=m.get("size", 0),
                        distance_to_centroid=dist,
                        z_score=z_score,
                    )
                )

        # Sort by distance (most outlying first)
        outliers.sort(key=lambda x: x.distance_to_centroid, reverse=True)

        return OutlierResult(
            species_name=species_name,
            total_images=len(species_metadata),
            outliers=outliers,
            outlier_count=len(outliers),
            threshold_percentile=threshold_percentile,
            computed_threshold=threshold,
            mean_distance=stats.get("mean_distance", mean_dist),
            std_distance=stats.get("std_distance", std_dist),
        )

    def get_all_outlier_counts(
        self,
        threshold_percentile: float = 95.0,
    ) -> dict[str, int]:
        """
        Get outlier counts for all species (for dashboard).

        Args:
            threshold_percentile: Percentile threshold to use

        Returns:
            Dict mapping species name to outlier count
        """
        counts = {}
        for species_name in self.species_stats.keys():
            try:
                result = self.detect_outliers(species_name, threshold_percentile)
                counts[species_name] = result.outlier_count
            except Exception:
                counts[species_name] = 0
        return counts


def create_outlier_service(embeddings_dir: Path) -> Optional[OutlierService]:
    """
    Factory function to create OutlierService if embeddings exist.

    Args:
        embeddings_dir: Directory containing embeddings

    Returns:
        OutlierService if files exist, None otherwise
    """
    required_files = ["metadata_full.pkl", "species_stats.json"]
    for filename in required_files:
        if not (embeddings_dir / filename).exists():
            return None

    return OutlierService(embeddings_dir)
