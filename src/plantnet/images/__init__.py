"""Image processing modules for PlantNet."""

from plantnet.images.deduplication import (
    DEFAULT_HAMMING_THRESHOLD,
    DEFAULT_HASH_SIZE,
    DeduplicationResult,
    compute_image_hash,
    deduplicate_species_images,
    find_duplicate_groups,
)
from plantnet.images.similarity import (
    DEFAULT_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    SimilarityResult,
    analyze_species_similarity,
    compute_cnn_embeddings,
    compute_cnn_embeddings_batch,
    find_similar_groups,
    load_model,
)

__all__ = [
    # Deduplication
    "DeduplicationResult",
    "deduplicate_species_images",
    "compute_image_hash",
    "find_duplicate_groups",
    "DEFAULT_HASH_SIZE",
    "DEFAULT_HAMMING_THRESHOLD",
    # Similarity
    "SimilarityResult",
    "load_model",
    "compute_cnn_embeddings",
    "compute_cnn_embeddings_batch",
    "find_similar_groups",
    "analyze_species_similarity",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "DEFAULT_MODEL",
]
