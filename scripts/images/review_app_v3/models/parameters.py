"""Analysis parameter Pydantic models."""

from typing import Literal

from pydantic import BaseModel, Field


class AnalysisParameters(BaseModel):
    """Parameters for analysis operations."""

    hash_size: int = Field(default=16, ge=8, le=32)
    hamming_threshold: int = Field(default=5, ge=0, le=20)
    similarity_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    threshold_percentile: float = Field(default=95.0, ge=80.0, le=99.0)


class ParameterInfo(BaseModel):
    """Description of a single parameter for UI display."""

    name: str = Field(description="Parameter key name")
    label: str = Field(description="Human-readable label")
    description: str = Field(description="Explanation of what the parameter does")
    type: Literal["int", "float"] = Field(description="Parameter data type")
    min: float = Field(description="Minimum allowed value")
    max: float = Field(description="Maximum allowed value")
    default: float = Field(description="Default value")
    step: float = Field(description="Step increment for slider")


class ParametersResponse(BaseModel):
    """Response with parameter descriptions and current values."""

    parameters: list[ParameterInfo] = Field(description="Parameter descriptions")
    current: AnalysisParameters = Field(description="Current parameter values")


# Parameter info for UI
PARAMETER_INFO: list[ParameterInfo] = [
    ParameterInfo(
        name="hash_size",
        label="Hash Size",
        description="Controls hash precision. Larger values are more precise but slower. 16 is recommended for most cases.",
        type="int",
        min=8,
        max=32,
        default=16,
        step=1,
    ),
    ParameterInfo(
        name="hamming_threshold",
        label="Duplicate Threshold",
        description="Maximum hash difference to consider images duplicates. 0 = exact matches only, 5 = allows minor differences.",
        type="int",
        min=0,
        max=20,
        default=5,
        step=1,
    ),
    ParameterInfo(
        name="similarity_threshold",
        label="Similarity Threshold",
        description="Minimum CNN similarity to group images. Higher = stricter. 0.95 = nearly identical, 0.70 = loosely similar.",
        type="float",
        min=0.5,
        max=1.0,
        default=0.85,
        step=0.05,
    ),
    ParameterInfo(
        name="threshold_percentile",
        label="Outlier Percentile",
        description="Images beyond this distance percentile are flagged as outliers. 95 = top 5% most unusual images.",
        type="float",
        min=80,
        max=99,
        default=95,
        step=1,
    ),
]
