"""Species-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel, Field


class SpeciesInfo(BaseModel):
    """Information about a single species."""

    name: str = Field(description="Species name (underscore-separated)")
    image_count: int = Field(ge=0, description="Total number of images")
    has_embeddings: bool = Field(description="Whether FAISS embeddings exist")
    processed: bool = Field(
        default=False, description="Whether this species has had confirmed deletions"
    )
    duplicate_count: Optional[int] = Field(
        default=None, description="Number of duplicate images detected"
    )
    similar_count: Optional[int] = Field(
        default=None, description="Number of images in similar groups"
    )
    outlier_count: Optional[int] = Field(
        default=None, description="Number of outlier images detected"
    )

    @property
    def total_issues(self) -> int:
        """Total number of flagged images."""
        return sum(
            c or 0 for c in [self.duplicate_count, self.similar_count, self.outlier_count]
        )


class SpeciesSummary(BaseModel):
    """Summary of all species for dashboard."""

    species: list[SpeciesInfo] = Field(description="List of all species")
    total_species: int = Field(ge=0, description="Total number of species")
    total_images: int = Field(ge=0, description="Total images across all species")
    species_with_issues: int = Field(
        ge=0, description="Number of species with detected issues"
    )
    faiss_available: bool = Field(description="Whether FAISS embeddings are loaded")
    cnn_available: bool = Field(description="Whether CNN model is available")


class AppStatus(BaseModel):
    """Application status information."""

    faiss_available: bool = Field(description="FAISS embeddings loaded")
    faiss_vector_count: Optional[int] = Field(
        default=None, description="Number of vectors in FAISS index"
    )
    cnn_available: bool = Field(description="CNN model available for on-demand computation")
    base_dir: str = Field(description="Base directory for species images")
    embeddings_dir: str = Field(description="Directory containing FAISS embeddings")
    species_count: int = Field(ge=0, description="Number of species directories found")
