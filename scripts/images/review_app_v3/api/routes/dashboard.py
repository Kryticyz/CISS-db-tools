"""
Dashboard API routes.

Provides species overview and application status endpoints.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends

# Add paths for imports
_package_dir = Path(__file__).parent.parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from config import get_settings
from models.species import AppStatus, SpeciesInfo, SpeciesSummary
from api.deps import (
    get_detection_service,
    get_faiss_store,
    get_outlier_service,
)
from services.detection_service import DetectionService
from services.outlier_service import OutlierService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=SpeciesSummary)
async def get_dashboard_summary(
    detection_service: DetectionService = Depends(get_detection_service),
) -> SpeciesSummary:
    """
    Get summary of all species with basic info.

    Returns species list with image counts. Issue counts (duplicates, similar,
    outliers) are NOT computed here to keep the dashboard fast. Use the
    individual analysis endpoints or /api/species/{name}/counts for that.
    """
    faiss_store = get_faiss_store()

    # Get species list
    species_names = detection_service.get_species_list()

    # Build species info list (fast - just counts files)
    species_list: list[SpeciesInfo] = []
    total_images = 0

    for name in species_names:
        info = detection_service.get_species_info(name)
        if info is None:
            continue

        species_list.append(info)
        total_images += info.image_count

    # Sort alphabetically for initial display
    species_list.sort(key=lambda x: x.name.lower())

    # Check CNN availability
    cnn_available = False
    try:
        from cnn_similarity import CNN_AVAILABLE
        cnn_available = CNN_AVAILABLE
    except ImportError:
        pass

    return SpeciesSummary(
        species=species_list,
        total_species=len(species_list),
        total_images=total_images,
        species_with_issues=0,  # Not computed for speed
        faiss_available=faiss_store is not None,
        cnn_available=cnn_available,
    )


@router.get("/species/{species_name}/counts")
async def get_species_counts(
    species_name: str,
    detection_service: DetectionService = Depends(get_detection_service),
    outlier_service: Optional[OutlierService] = Depends(get_outlier_service),
) -> dict:
    """
    Get issue counts for a single species (for lazy loading).

    This endpoint computes duplicate, similar, and outlier counts
    for one species at a time to avoid blocking the dashboard.
    """
    settings = get_settings()

    counts = {
        "species": species_name,
        "duplicate_count": 0,
        "similar_count": 0,
        "outlier_count": 0,
    }

    # Get duplicate count
    try:
        dup_result = detection_service.get_duplicates(
            species_name,
            settings.default_hash_size,
            settings.default_hamming_threshold,
        )
        counts["duplicate_count"] = dup_result.total_duplicates
    except Exception:
        pass

    # Get similarity count
    try:
        sim_result = detection_service.get_similarity(
            species_name,
            settings.default_similarity_threshold,
        )
        counts["similar_count"] = sum(
            g.count - 1 for g in sim_result.similar_groups
        )
    except Exception:
        pass

    # Get outlier count
    if outlier_service is not None:
        try:
            outlier_result = outlier_service.detect_outliers(
                species_name,
                settings.default_threshold_percentile,
            )
            counts["outlier_count"] = outlier_result.outlier_count
        except Exception:
            pass

    return counts


@router.get("/status", response_model=AppStatus)
async def get_app_status(
    detection_service: DetectionService = Depends(get_detection_service),
) -> AppStatus:
    """
    Get application status information.

    Returns availability of FAISS, CNN, and other configuration.
    """
    settings = get_settings()
    faiss_store = get_faiss_store()

    # Check CNN availability
    cnn_available = False
    try:
        from cnn_similarity import CNN_AVAILABLE
        cnn_available = CNN_AVAILABLE
    except ImportError:
        pass

    species_list = detection_service.get_species_list()

    return AppStatus(
        faiss_available=faiss_store is not None,
        faiss_vector_count=faiss_store.index.ntotal if faiss_store else None,
        cnn_available=cnn_available,
        base_dir=str(settings.base_dir),
        embeddings_dir=str(settings.embeddings_dir),
        species_count=len(species_list),
    )
