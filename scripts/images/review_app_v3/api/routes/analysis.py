"""
Analysis API routes.

Provides duplicate, similarity, and outlier detection endpoints.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

# Add paths for imports
_package_dir = Path(__file__).parent.parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from config import get_settings
from models.analysis import (
    CombinedAnalysis,
    DuplicateResult,
    OutlierResult,
    SimilarityResult,
)
from models.parameters import (
    AnalysisParameters,
    PARAMETER_INFO,
    ParametersResponse,
)
from api.deps import (
    get_detection_service,
    get_outlier_service,
    validate_species,
    validate_species_has_embeddings,
)
from services.detection_service import DetectionService
from services.outlier_service import OutlierService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/parameters", response_model=ParametersResponse)
async def get_parameters() -> ParametersResponse:
    """
    Get parameter descriptions and current defaults.

    Returns information about each parameter for UI display.
    """
    settings = get_settings()

    return ParametersResponse(
        parameters=PARAMETER_INFO,
        current=AnalysisParameters(
            hash_size=settings.default_hash_size,
            hamming_threshold=settings.default_hamming_threshold,
            similarity_threshold=settings.default_similarity_threshold,
            threshold_percentile=settings.default_threshold_percentile,
        ),
    )


@router.get("/duplicates/{species}", response_model=DuplicateResult)
async def get_duplicates(
    species: str = Depends(validate_species),
    hash_size: int = Query(default=16, ge=8, le=32),
    hamming_threshold: int = Query(default=5, ge=0, le=20),
    detection_service: DetectionService = Depends(get_detection_service),
) -> DuplicateResult:
    """
    Detect duplicate images using perceptual hashing.

    Args:
        species: Species name to analyze
        hash_size: Hash precision (8-32, default 16)
        hamming_threshold: Max hash difference for duplicates (0-20, default 5)

    Returns:
        DuplicateResult with grouped duplicates
    """
    return detection_service.get_duplicates(
        species_name=species,
        hash_size=hash_size,
        hamming_threshold=hamming_threshold,
    )


@router.get("/similar/{species}", response_model=SimilarityResult)
async def get_similar(
    species: str = Depends(validate_species_has_embeddings),
    similarity_threshold: float = Query(default=0.85, ge=0.5, le=1.0),
    detection_service: DetectionService = Depends(get_detection_service),
) -> SimilarityResult:
    """
    Detect similar images using CNN embeddings.

    Requires pre-computed FAISS embeddings for the species.

    Args:
        species: Species name to analyze
        similarity_threshold: Minimum cosine similarity (0.5-1.0, default 0.85)

    Returns:
        SimilarityResult with grouped similar images
    """
    return detection_service.get_similarity(
        species_name=species,
        similarity_threshold=similarity_threshold,
    )


@router.get("/outliers/{species}", response_model=OutlierResult)
async def get_outliers(
    species: str = Depends(validate_species_has_embeddings),
    threshold_percentile: float = Query(default=95.0, ge=80.0, le=99.0),
    outlier_service: Optional[OutlierService] = Depends(get_outlier_service),
) -> OutlierResult:
    """
    Detect outlier images using centroid distance.

    Images with distance from species centroid above the
    specified percentile are flagged as outliers.

    Args:
        species: Species name to analyze
        threshold_percentile: Percentile above which images are outliers (80-99)

    Returns:
        OutlierResult with detected outliers
    """
    if outlier_service is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outlier detection not available. Missing embeddings files.",
        )

    return outlier_service.detect_outliers(
        species_name=species,
        threshold_percentile=threshold_percentile,
    )


@router.get("/combined/{species}", response_model=CombinedAnalysis)
async def get_combined_analysis(
    species: str = Depends(validate_species_has_embeddings),
    hash_size: int = Query(default=16, ge=8, le=32),
    hamming_threshold: int = Query(default=5, ge=0, le=20),
    similarity_threshold: float = Query(default=0.85, ge=0.5, le=1.0),
    threshold_percentile: float = Query(default=95.0, ge=80.0, le=99.0),
    detection_service: DetectionService = Depends(get_detection_service),
    outlier_service: Optional[OutlierService] = Depends(get_outlier_service),
) -> CombinedAnalysis:
    """
    Get all three analyses combined for a species.

    Args:
        species: Species name to analyze
        hash_size: Hash precision for duplicate detection
        hamming_threshold: Max hash difference for duplicates
        similarity_threshold: Min cosine similarity for similar images
        threshold_percentile: Percentile for outlier detection

    Returns:
        CombinedAnalysis with all three analysis results
    """
    # Get duplicates
    duplicates = detection_service.get_duplicates(
        species_name=species,
        hash_size=hash_size,
        hamming_threshold=hamming_threshold,
    )

    # Get similar images
    similar = detection_service.get_similarity(
        species_name=species,
        similarity_threshold=similarity_threshold,
    )

    # Get outliers
    if outlier_service is not None:
        outliers = outlier_service.detect_outliers(
            species_name=species,
            threshold_percentile=threshold_percentile,
        )
    else:
        outliers = OutlierResult(
            species_name=species,
            total_images=0,
            outliers=[],
            outlier_count=0,
            threshold_percentile=threshold_percentile,
            computed_threshold=0.0,
            mean_distance=0.0,
            std_distance=0.0,
        )

    return CombinedAnalysis(
        species_name=species,
        duplicates=duplicates,
        similar=similar,
        outliers=outliers,
    )
