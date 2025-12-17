"""
Application configuration and settings.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Paths - set at runtime via CLI or environment
    base_dir: Path = Field(
        default=Path("data/images/by_species"),
        description="Base directory containing species image folders",
    )
    embeddings_dir: Path = Field(
        default=Path("data/databases/embeddings"),
        description="Directory containing FAISS embeddings",
    )

    # Requirements
    require_embeddings: bool = Field(
        default=True,
        description="Fail startup if embeddings not found",
    )

    # Analysis defaults
    default_hash_size: int = Field(default=16, ge=8, le=32)
    default_hamming_threshold: int = Field(default=5, ge=0, le=20)
    default_similarity_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    default_threshold_percentile: float = Field(default=95.0, ge=80.0, le=99.0)

    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins for React dev server",
    )

    model_config = {"env_prefix": "PLANTNET_"}


# Global settings instance - will be configured at startup
settings: Optional[Settings] = None


def init_settings(
    base_dir: Optional[Path] = None,
    embeddings_dir: Optional[Path] = None,
    **kwargs,
) -> Settings:
    """Initialize settings with optional overrides."""
    global settings

    overrides = {}
    if base_dir is not None:
        overrides["base_dir"] = base_dir
    if embeddings_dir is not None:
        overrides["embeddings_dir"] = embeddings_dir
    overrides.update(kwargs)

    settings = Settings(**overrides)
    return settings


def get_settings() -> Settings:
    """Get current settings, initializing with defaults if needed."""
    global settings
    if settings is None:
        settings = Settings()
    return settings
