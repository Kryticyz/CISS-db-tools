"""
FastAPI dependency injection configuration.

Provides singleton instances of services to API routes.
"""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, status

# Add paths for imports
_package_dir = Path(__file__).parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))
_scripts_images_dir = _package_dir.parent
if str(_scripts_images_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_images_dir))

# Import existing core modules
from review_app.core.storage import FAISSEmbeddingStore, init_faiss_store

from config import get_settings, Settings
from services.deletion_queue import DeletionQueueService
from services.detection_service import DetectionService
from services.outlier_service import OutlierService


# Singleton instances (initialized at startup)
_faiss_store: Optional[FAISSEmbeddingStore] = None
_detection_service: Optional[DetectionService] = None
_outlier_service: Optional[OutlierService] = None
_deletion_queue: Optional[DeletionQueueService] = None


def init_services(settings: Settings) -> None:
    """
    Initialize all services at application startup.

    Args:
        settings: Application settings

    Raises:
        RuntimeError: If required embeddings are missing
    """
    global _faiss_store, _detection_service, _outlier_service, _deletion_queue

    # Initialize FAISS store
    if settings.embeddings_dir.exists():
        _faiss_store = init_faiss_store(settings.embeddings_dir)

    if _faiss_store is None and settings.require_embeddings:
        raise RuntimeError(
            f"FAISS embeddings required but not found at {settings.embeddings_dir}. "
            f"Run batch_generate_embeddings.py first."
        )

    # Initialize detection service
    _detection_service = DetectionService(
        base_dir=settings.base_dir,
        faiss_store=_faiss_store,
    )

    # Initialize outlier service
    if settings.embeddings_dir.exists():
        try:
            _outlier_service = OutlierService(settings.embeddings_dir)
        except FileNotFoundError:
            _outlier_service = None

    # Initialize deletion queue
    _deletion_queue = DeletionQueueService(settings.base_dir)


def get_faiss_store() -> Optional[FAISSEmbeddingStore]:
    """Get FAISS store instance."""
    return _faiss_store


def get_detection_service() -> DetectionService:
    """Get detection service instance."""
    if _detection_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Detection service not initialized",
        )
    return _detection_service


def get_outlier_service() -> Optional[OutlierService]:
    """Get outlier service instance (may be None)."""
    return _outlier_service


def get_deletion_queue() -> DeletionQueueService:
    """Get deletion queue service instance."""
    if _deletion_queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deletion queue not initialized",
        )
    return _deletion_queue


def validate_species(
    species: str,
    detection_service: DetectionService = Depends(get_detection_service),
) -> str:
    """
    Validate that a species exists.

    Args:
        species: Species name to validate

    Returns:
        The validated species name

    Raises:
        HTTPException: If species not found
    """
    species_list = detection_service.get_species_list()

    if species not in species_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Species not found: {species}",
        )

    return species


def validate_species_has_embeddings(
    species: str = Depends(validate_species),
    faiss_store: Optional[FAISSEmbeddingStore] = Depends(get_faiss_store),
) -> str:
    """
    Validate that a species has FAISS embeddings.

    Args:
        species: Species name to validate
        faiss_store: FAISS store instance

    Returns:
        The validated species name

    Raises:
        HTTPException: If species has no embeddings
    """
    if faiss_store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FAISS embeddings not available",
        )

    species_in_faiss = {m["species"] for m in faiss_store.metadata}
    if species not in species_in_faiss:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Species '{species}' has no pre-computed embeddings. "
            f"Run batch_generate_embeddings.py first.",
        )

    return species
