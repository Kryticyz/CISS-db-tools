"""Pydantic models for API requests and responses."""

import sys
from pathlib import Path

# Ensure package is in path
_package_dir = Path(__file__).parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from models.analysis import (
    CombinedAnalysis,
    DuplicateGroup,
    DuplicateResult,
    ImageInfo,
    OutlierInfo,
    OutlierResult,
    SimilarGroup,
    SimilarityResult,
)
from models.deletion import (
    DeletionPreview,
    DeletionReason,
    DeletionResult,
    DeletionQueue,
    QueuedFile,
)
from models.parameters import AnalysisParameters, ParameterInfo, ParametersResponse
from models.species import SpeciesInfo, SpeciesSummary

__all__ = [
    # Species
    "SpeciesInfo",
    "SpeciesSummary",
    # Analysis
    "ImageInfo",
    "DuplicateGroup",
    "DuplicateResult",
    "SimilarGroup",
    "SimilarityResult",
    "OutlierInfo",
    "OutlierResult",
    "CombinedAnalysis",
    # Parameters
    "AnalysisParameters",
    "ParameterInfo",
    "ParametersResponse",
    # Deletion
    "DeletionReason",
    "QueuedFile",
    "DeletionQueue",
    "DeletionPreview",
    "DeletionResult",
]
