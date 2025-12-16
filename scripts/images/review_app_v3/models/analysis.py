"""Analysis result Pydantic models."""

from typing import Optional

from pydantic import BaseModel, Field


class ImageInfo(BaseModel):
    """Information about a single image."""

    filename: str = Field(description="Image filename")
    path: str = Field(description="API path to serve image")
    size: int = Field(ge=0, description="File size in bytes")
    hash: Optional[str] = Field(default=None, description="Perceptual hash value")


class DuplicateGroup(BaseModel):
    """A group of duplicate images."""

    group_id: int = Field(ge=1, description="Unique group identifier")
    keep: ImageInfo = Field(description="Image to keep (largest file)")
    duplicates: list[ImageInfo] = Field(description="Images to delete")
    total_in_group: int = Field(ge=2, description="Total images in group")


class DuplicateResult(BaseModel):
    """Result of hash-based duplicate detection."""

    species_name: str = Field(description="Species analyzed")
    total_images: int = Field(ge=0, description="Total images in species")
    hashed_images: int = Field(ge=0, description="Images successfully hashed")
    duplicate_groups: list[DuplicateGroup] = Field(description="Groups of duplicates")
    total_duplicates: int = Field(ge=0, description="Total duplicate images to delete")
    hash_size: int = Field(description="Hash size used")
    hamming_threshold: int = Field(description="Hamming distance threshold used")


class SimilarGroup(BaseModel):
    """A group of similar images."""

    group_id: int = Field(ge=1, description="Unique group identifier")
    images: list[ImageInfo] = Field(description="Similar images in group")
    count: int = Field(ge=2, description="Number of images in group")
    avg_similarity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Average pairwise similarity"
    )


class SimilarityResult(BaseModel):
    """Result of CNN-based similarity detection."""

    species_name: str = Field(description="Species analyzed")
    total_images: int = Field(ge=0, description="Total images in species")
    processed_images: int = Field(ge=0, description="Images with embeddings")
    similar_groups: list[SimilarGroup] = Field(description="Groups of similar images")
    total_in_groups: int = Field(ge=0, description="Total images in similar groups")
    similarity_threshold: float = Field(description="Similarity threshold used")
    model_name: str = Field(description="CNN model used")
    from_faiss: bool = Field(default=False, description="Whether results came from FAISS")


class OutlierInfo(BaseModel):
    """Information about an outlier image."""

    filename: str = Field(description="Image filename")
    path: str = Field(description="API path to serve image")
    size: int = Field(ge=0, description="File size in bytes")
    distance_to_centroid: float = Field(
        ge=0.0, description="Cosine distance from species centroid"
    )
    z_score: Optional[float] = Field(
        default=None, description="Z-score based on species distribution"
    )


class OutlierResult(BaseModel):
    """Result of outlier detection."""

    species_name: str = Field(description="Species analyzed")
    total_images: int = Field(ge=0, description="Total images in species")
    outliers: list[OutlierInfo] = Field(description="Detected outlier images")
    outlier_count: int = Field(ge=0, description="Number of outliers")
    threshold_percentile: float = Field(description="Percentile threshold used")
    computed_threshold: float = Field(description="Computed distance threshold")
    mean_distance: float = Field(description="Mean distance for species")
    std_distance: float = Field(description="Standard deviation of distances")


class CombinedAnalysis(BaseModel):
    """Combined analysis results for a species."""

    species_name: str = Field(description="Species analyzed")
    duplicates: DuplicateResult = Field(description="Duplicate detection results")
    similar: SimilarityResult = Field(description="Similarity detection results")
    outliers: OutlierResult = Field(description="Outlier detection results")
