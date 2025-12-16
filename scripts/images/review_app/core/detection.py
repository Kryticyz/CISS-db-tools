"""
Core detection logic for duplicates and CNN similarity.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import deduplication module
try:
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )


# Try to import CNN similarity module
CNN_AVAILABLE = False
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_MODEL = "resnet18"

try:
    from cnn_similarity import (
        DEFAULT_MODEL,
        DEFAULT_SIMILARITY_THRESHOLD,
        compute_cnn_embeddings,
        cosine_similarity,
        embeddings_to_json,
    )
    from cnn_similarity import find_similar_groups as find_cnn_similar_groups

    CNN_AVAILABLE = True
except ImportError:
    pass


def get_species_list(base_dir: Path) -> List[str]:
    """Get list of species directories."""
    if base_dir is None:
        return []

    species = []
    for item in sorted(base_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has images
            image_count = len(get_image_files(item))
            if image_count > 0:
                species.append(item.name)

    return species


def get_species_hashes(
    base_dir: Path, species_name: str, hash_size: int, hash_cache: Dict
) -> Dict[str, Any]:
    """
    Get image hashes for a species (without grouping).

    Returns dict with hash values for each image.
    """
    species_dir = base_dir / species_name
    if not species_dir.exists():
        return {"error": f"Species directory not found: {species_name}"}

    image_files = get_image_files(species_dir)

    # Check cache
    cache_key = f"{species_name}_{hash_size}"
    if cache_key not in hash_cache:
        # Compute hashes
        hash_map: Dict[Path, str] = {}

        for img_path in image_files:
            result = compute_image_hash(img_path, hash_size, True)
            if result:
                path, img_hash, error = result
                if not error and img_hash:
                    hash_map[path] = img_hash

        hash_cache[cache_key] = hash_map
    else:
        hash_map = hash_cache[cache_key]

    # Build image info with hashes
    images = []
    for img_path in image_files:
        img_info = {
            "filename": img_path.name,
            "size": img_path.stat().st_size,
            "path": f"/image/{species_name}/{img_path.name}",
            "hash": hash_map.get(img_path, None),
        }
        images.append(img_info)

    return {
        "species_name": species_name,
        "hash_size": hash_size,
        "total_images": len(image_files),
        "hashed_images": len(hash_map),
        "images": images,
    }


def get_species_duplicates(
    base_dir: Path,
    species_name: str,
    hash_size: int,
    hamming_threshold: int,
    hash_cache: Dict,
) -> Dict[str, Any]:
    """
    Get duplicate groups for a species.

    Returns dict with duplicate group information.
    """
    species_dir = base_dir / species_name
    if not species_dir.exists():
        return {"error": f"Species directory not found: {species_name}"}

    image_files = get_image_files(species_dir)

    if len(image_files) < 2:
        return {
            "species_name": species_name,
            "total_images": len(image_files),
            "duplicate_groups": [],
            "images": [],
            "message": "Not enough images for duplicate detection",
        }

    # Check cache
    cache_key = f"{species_name}_{hash_size}"
    if cache_key not in hash_cache:
        # Compute hashes
        hash_map: Dict[Path, str] = {}
        errors = []

        for img_path in image_files:
            result = compute_image_hash(img_path, hash_size, True)
            if result:
                path, img_hash, error = result
                if error:
                    errors.append({"file": path.name, "error": error})
                elif img_hash:
                    hash_map[path] = img_hash

        hash_cache[cache_key] = hash_map
    else:
        hash_map = hash_cache[cache_key]

    # Build image info with hashes (for client-side caching)
    images = []
    for img_path in image_files:
        img_info = {
            "filename": img_path.name,
            "size": img_path.stat().st_size,
            "path": f"/image/{species_name}/{img_path.name}",
            "hash": hash_map.get(img_path, None),
        }
        images.append(img_info)

    # Find duplicate groups with current threshold
    duplicate_groups = find_duplicate_groups(hash_map, hamming_threshold)

    # Format results
    groups = []
    for i, group in enumerate(duplicate_groups, 1):
        keep, delete = select_images_to_keep(group)

        group_info = {
            "group_id": i,
            "keep": {
                "filename": keep.name,
                "size": keep.stat().st_size,
                "path": f"/image/{species_name}/{keep.name}",
                "hash": hash_map.get(keep, None),
            },
            "duplicates": [
                {
                    "filename": p.name,
                    "size": p.stat().st_size,
                    "path": f"/image/{species_name}/{p.name}",
                    "hash": hash_map.get(p, None),
                }
                for p in delete
            ],
            "total_in_group": len(group),
        }
        groups.append(group_info)

    return {
        "species_name": species_name,
        "total_images": len(image_files),
        "hashed_images": len(hash_map),
        "duplicate_groups": groups,
        "total_duplicates": sum(len(g["duplicates"]) for g in groups),
        "hash_size": hash_size,
        "hamming_threshold": hamming_threshold,
        "images": images,
    }


def get_all_species_duplicates(
    base_dir: Path, hash_size: int, hamming_threshold: int, hash_cache: Dict
) -> Dict[str, Any]:
    """
    Get duplicate groups for ALL species.

    Returns dict with duplicate group information for every species.
    """
    species_list = get_species_list(base_dir)

    all_results = []
    total_images = 0
    total_duplicates = 0
    total_groups = 0
    species_with_duplicates = 0

    for species_name in species_list:
        result = get_species_duplicates(
            base_dir, species_name, hash_size, hamming_threshold, hash_cache
        )

        if "error" not in result:
            total_images += result.get("total_images", 0)
            species_duplicates = result.get("total_duplicates", 0)
            total_duplicates += species_duplicates
            total_groups += len(result.get("duplicate_groups", []))

            if species_duplicates > 0:
                species_with_duplicates += 1
                all_results.append(result)

    return {
        "mode": "all_species",
        "total_species_scanned": len(species_list),
        "species_with_duplicates": species_with_duplicates,
        "total_images": total_images,
        "total_duplicates": total_duplicates,
        "total_groups": total_groups,
        "hash_size": hash_size,
        "hamming_threshold": hamming_threshold,
        "species_results": all_results,
    }


def get_species_cnn_similarity(
    base_dir: Path,
    species_name: str,
    similarity_threshold: float,
    model_name: str,
    cnn_cache: Dict,
    faiss_store: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Get CNN-based similar image groups for a species.

    Now uses pre-computed embeddings from FAISS if available,
    otherwise falls back to on-demand computation.

    Returns dict with similar group information.
    """
    # Try FAISS first (instant)
    if faiss_store is not None:
        try:
            similar_groups = faiss_store.search_species(
                species_name, similarity_threshold
            )

            total_in_groups = sum(g["count"] for g in similar_groups)

            return {
                "species_name": species_name,
                "total_images": total_in_groups,
                "processed_images": total_in_groups,
                "similar_groups": similar_groups,
                "total_in_groups": total_in_groups,
                "similarity_threshold": similarity_threshold,
                "model_name": "pre-computed",
                "cnn_available": True,
                "from_faiss": True,
            }
        except Exception as e:
            print(f"FAISS search failed, falling back to on-demand: {e}")

    # Fallback to original on-demand computation
    if not CNN_AVAILABLE:
        return {"error": "CNN similarity not available. Install torch and torchvision."}

    species_dir = base_dir / species_name
    if not species_dir.exists():
        return {"error": f"Species directory not found: {species_name}"}

    image_files = get_image_files(species_dir)

    if len(image_files) < 2:
        return {
            "species_name": species_name,
            "total_images": len(image_files),
            "similar_groups": [],
            "images": [],
            "message": "Not enough images for similarity detection",
        }

    # Check cache
    cache_key = f"{species_name}_{model_name}"
    if cache_key not in cnn_cache:
        # Compute embeddings
        embeddings, errors = compute_cnn_embeddings(
            image_files, model_name, verbose=True
        )
        cnn_cache[cache_key] = embeddings
    else:
        embeddings = cnn_cache[cache_key]

    # Build image info with embeddings
    images = []
    for img_path in image_files:
        embedding = embeddings.get(img_path)
        img_info = {
            "filename": img_path.name,
            "size": img_path.stat().st_size,
            "path": f"/image/{species_name}/{img_path.name}",
            "embedding": embedding,
        }
        images.append(img_info)

    # Find similar groups
    similar_groups_raw = find_cnn_similar_groups(embeddings, similarity_threshold)

    # Format results
    groups = []
    for i, group in enumerate(similar_groups_raw, 1):
        sorted_group = sorted(group, key=lambda p: (-p.stat().st_size, p.name))

        group_images = []
        for img_path in sorted_group:
            group_images.append(
                {
                    "filename": img_path.name,
                    "size": img_path.stat().st_size,
                    "path": f"/image/{species_name}/{img_path.name}",
                }
            )

        groups.append(
            {
                "group_id": i,
                "images": group_images,
                "count": len(group_images),
            }
        )

    return {
        "species_name": species_name,
        "total_images": len(image_files),
        "processed_images": len(embeddings),
        "similar_groups": groups,
        "total_in_groups": sum(g["count"] for g in groups),
        "similarity_threshold": similarity_threshold,
        "model_name": model_name,
        "images": images,
        "cnn_available": True,
    }


def get_all_species_cnn_similarity(
    base_dir: Path,
    similarity_threshold: float,
    model_name: str,
    cnn_cache: Dict,
    faiss_store: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Get CNN-based similar image groups across ALL species.

    Returns dict with similar group information for every species.
    """
    species_list = get_species_list(base_dir)

    all_results = []
    total_images = 0
    total_groups = 0
    species_with_similarities = 0

    for species_name in species_list:
        result = get_species_cnn_similarity(
            base_dir,
            species_name,
            similarity_threshold,
            model_name,
            cnn_cache,
            faiss_store,
        )

        if "error" not in result:
            species_images = result.get("total_images", 0)
            total_images += species_images
            species_groups = len(result.get("similar_groups", []))
            total_groups += species_groups

            if species_groups > 0:
                species_with_similarities += 1
                all_results.append(result)

    return {
        "mode": "all_species_cnn",
        "total_species_scanned": len(species_list),
        "species_with_similarities": species_with_similarities,
        "total_images": total_images,
        "total_groups": total_groups,
        "similarity_threshold": similarity_threshold,
        "model_name": model_name,
        "species_results": all_results,
    }


def delete_files(base_dir: Path, file_paths: List[str]) -> Dict[str, Any]:
    """
    Delete the specified files.

    Args:
        base_dir: Base directory for security validation
        file_paths: List of relative paths like "species_name/filename.jpg"

    Returns:
        Dict with deletion results
    """
    deleted = []
    errors = []

    for rel_path in file_paths:
        try:
            # Security: validate path
            full_path = (base_dir / rel_path).resolve()
            if not full_path.is_relative_to(base_dir.resolve()):
                errors.append({"path": rel_path, "error": "Invalid path"})
                continue

            if not full_path.exists():
                errors.append({"path": rel_path, "error": "File not found"})
                continue

            # Delete the file
            full_path.unlink()
            deleted.append(rel_path)
            print(f"Deleted: {rel_path}")

        except Exception as e:
            errors.append({"path": rel_path, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "deleted_count": len(deleted),
        "deleted": deleted,
        "error_count": len(errors),
        "errors": errors,
    }
