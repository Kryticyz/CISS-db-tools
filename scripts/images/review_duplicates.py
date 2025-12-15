#!/usr/bin/env python3
"""
Web-based Duplicate Image Review Tool

A local web server that provides a visual interface for reviewing duplicate
image groups detected by the deduplication system. Useful for:
- Verifying that detected duplicates are actually similar
- Tuning threshold values for perceptual hashing
- Reviewing deduplication results before deletion

Usage:
    python review_duplicates.py /path/to/by_species
    python review_duplicates.py /path/to/by_species --port 8080
    python review_duplicates.py /path/to/by_species --threshold 3 --rescan

Then open http://localhost:8000 in your browser.

Dependencies:
    pip install Pillow imagehash torch torchvision
"""

import argparse
import http.server
import json
import mimetypes
import os
import socketserver
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import deduplication module
try:
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        IMAGE_EXTENSIONS,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        IMAGE_EXTENSIONS,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )


# Try to import CNN similarity module
CNN_AVAILABLE = False
try:
    from cnn_similarity import (
        DEFAULT_MODEL,
        DEFAULT_SIMILARITY_THRESHOLD,
        compute_cnn_embeddings,
        cosine_similarity,
        embeddings_to_json,
    )
    from cnn_similarity import (
        find_similar_groups as find_cnn_similar_groups,
    )

    CNN_AVAILABLE = True
except ImportError:
    DEFAULT_SIMILARITY_THRESHOLD = 0.85
    DEFAULT_MODEL = "resnet18"


# Global configuration
BASE_DIR: Optional[Path] = None
CURRENT_CONFIG: Dict[str, Any] = {
    "hash_size": DEFAULT_HASH_SIZE,
    "hamming_threshold": DEFAULT_HAMMING_THRESHOLD,
}

# Cache for computed hashes
HASH_CACHE: Dict[str, Dict[Path, str]] = {}

# Cache for CNN embeddings
CNN_CACHE: Dict[str, Dict[Path, List[float]]] = {}

# FAISS embedding store
FAISS_STORE: Optional[Any] = None
EMBEDDINGS_DIR = Path("data/databases/embeddings")


class FAISSEmbeddingStore:
    """FAISS-based embedding store for fast similarity search."""

    def __init__(self, embeddings_dir: Path):
        try:
            import pickle

            import faiss
        except ImportError:
            raise ImportError(
                "FAISS not available. Install with: pip install faiss-cpu"
            )

        self.embeddings_dir = embeddings_dir
        self.index = faiss.read_index(str(embeddings_dir / "embeddings.index"))

        with open(embeddings_dir / "metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)

        print(f"Loaded FAISS index with {self.index.ntotal} vectors")

    def search_species(self, species_name: str, threshold: float = 0.85):
        """Find similar images within a species using cached embeddings."""
        try:
            import pickle

            import faiss
            import numpy as np
        except ImportError:
            return []

        # Get all images for this species
        species_items = [m for m in self.metadata if m["species"] == species_name]
        if len(species_items) < 2:
            return []

        # Get their indices in the FAISS index
        species_indices = [
            i for i, m in enumerate(self.metadata) if m["species"] == species_name
        ]

        # Extract their embeddings
        # (We need full metadata for this - load it)
        with open(self.embeddings_dir / "metadata_full.pkl", "rb") as f:
            full_metadata = pickle.load(f)

        species_embeddings = [full_metadata[i]["embedding"] for i in species_indices]
        embeddings_array = np.array(species_embeddings, dtype="float32")
        faiss.normalize_L2(embeddings_array)

        # Find similar pairs using threshold
        n = len(species_embeddings)

        # Union-Find for grouping
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[py] = px

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                sim = np.dot(embeddings_array[i], embeddings_array[j])
                if sim >= threshold:
                    union(i, j)

        # Group by root
        groups_dict = {}
        for i in range(n):
            root = find(i)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(species_items[i])

        # Format as groups (only groups with >1 image)
        result_groups = []
        group_id = 1
        for group_items in groups_dict.values():
            if len(group_items) > 1:
                # Sort by size
                group_items.sort(key=lambda x: -x["size"])
                result_groups.append(
                    {
                        "group_id": group_id,
                        "images": [
                            {
                                "filename": item["filename"],
                                "size": item["size"],
                                "path": f"/image/{species_name}/{item['filename']}",
                            }
                            for item in group_items
                        ],
                        "count": len(group_items),
                    }
                )
                group_id += 1

        return result_groups


def init_faiss_store():
    """Initialize FAISS store if embeddings exist."""
    global FAISS_STORE

    if EMBEDDINGS_DIR.exists() and (EMBEDDINGS_DIR / "embeddings.index").exists():
        try:
            FAISS_STORE = FAISSEmbeddingStore(EMBEDDINGS_DIR)
            return True
        except Exception as e:
            print(f"Warning: Could not load FAISS store: {e}")
            return False
    return False


# Initialize on module load
FAISS_AVAILABLE = init_faiss_store()


def get_species_list() -> List[str]:
    """Get list of species directories."""
    if BASE_DIR is None:
        return []

    species = []
    for item in sorted(BASE_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has images
            image_count = len(get_image_files(item))
            if image_count > 0:
                species.append(item.name)

    return species


def get_species_hashes(species_name: str, hash_size: int) -> Dict[str, Any]:
    """
    Get image hashes for a species (without grouping).

    Returns dict with hash values for each image.
    """
    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_dir = BASE_DIR / species_name
    if not species_dir.exists():
        return {"error": f"Species directory not found: {species_name}"}

    image_files = get_image_files(species_dir)

    # Check cache
    cache_key = f"{species_name}_{hash_size}"
    if cache_key not in HASH_CACHE:
        # Compute hashes
        hash_map: Dict[Path, str] = {}

        for img_path in image_files:
            result = compute_image_hash(img_path, hash_size, True)
            if result:
                path, img_hash, error = result
                if not error and img_hash:
                    hash_map[path] = img_hash

        HASH_CACHE[cache_key] = hash_map
    else:
        hash_map = HASH_CACHE[cache_key]

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
    species_name: str, hash_size: int, hamming_threshold: int
) -> Dict[str, Any]:
    """
    Get duplicate groups for a species.

    Returns dict with duplicate group information.
    """
    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_dir = BASE_DIR / species_name
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
    if cache_key not in HASH_CACHE:
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

        HASH_CACHE[cache_key] = hash_map
    else:
        hash_map = HASH_CACHE[cache_key]

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
    hash_size: int, hamming_threshold: int
) -> Dict[str, Any]:
    """
    Get duplicate groups for ALL species.

    Returns dict with duplicate group information for every species.
    """
    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_list = get_species_list()

    all_results = []
    total_images = 0
    total_duplicates = 0
    total_groups = 0
    species_with_duplicates = 0

    for species_name in species_list:
        result = get_species_duplicates(species_name, hash_size, hamming_threshold)

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
    species_name: str, similarity_threshold: float, model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Get CNN-based similar image groups for a species.

    Now uses pre-computed embeddings from FAISS if available,
    otherwise falls back to on-demand computation.

    Returns dict with similar group information.
    """
    # Try FAISS first (instant)
    if FAISS_STORE is not None:
        try:
            similar_groups = FAISS_STORE.search_species(
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

    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_dir = BASE_DIR / species_name
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
    if cache_key not in CNN_CACHE:
        # Compute embeddings
        embeddings, errors = compute_cnn_embeddings(
            image_files, model_name, verbose=True
        )
        CNN_CACHE[cache_key] = embeddings
    else:
        embeddings = CNN_CACHE[cache_key]

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


def delete_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Delete the specified files.

    Args:
        file_paths: List of relative paths like "species_name/filename.jpg"

    Returns:
        Dict with deletion results
    """
    if BASE_DIR is None:
        return {"success": False, "error": "Base directory not configured"}

    deleted = []
    errors = []

    for rel_path in file_paths:
        try:
            # Security: validate path
            full_path = (BASE_DIR / rel_path).resolve()
            if not full_path.is_relative_to(BASE_DIR.resolve()):
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


def generate_html_page() -> str:
    """Generate the main HTML page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Duplicate Image Review</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: #16213e;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        h1 {
            color: #e94560;
            margin-bottom: 10px;
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: flex-end;
            margin-top: 15px;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .control-group label {
            font-size: 12px;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        select, input[type="number"], button {
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }

        select, input[type="number"] {
            background: #0f3460;
            color: #fff;
            min-width: 200px;
        }

        select:focus, input[type="number"]:focus {
            outline: 2px solid #e94560;
        }

        button {
            background: #e94560;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s, transform 0.1s;
        }

        button:hover {
            background: #ff6b6b;
        }

        button:active {
            transform: scale(0.98);
        }

        button:disabled {
            background: #555;
            cursor: not-allowed;
            transform: none;
        }

        button.secondary {
            background: #0f3460;
        }

        button.secondary:hover {
            background: #1a4a7a;
        }

        button.secondary.active {
            background: #4ecca3;
            color: #000;
        }

        button.confirm-btn {
            background: #4ecca3;
            color: #000;
            font-size: 12px;
            padding: 6px 12px;
        }

        button.confirm-btn:hover {
            background: #3db892;
        }

        button.confirm-btn.confirmed {
            background: #2d8a6e;
            color: #fff;
        }

        button.delete-btn {
            background: #dc3545;
        }

        button.delete-btn:hover {
            background: #c82333;
        }

        .mode-buttons {
            display: flex;
            gap: 10px;
        }

        .action-bar {
            background: #0f3460;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .action-bar-left {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .action-bar-right {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .confirmed-count {
            background: #4ecca3;
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }

        .stats {
            background: #16213e;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #e94560;
        }

        .stat-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }

        .loading {
            text-align: center;
            padding: 50px;
            color: #888;
        }

        .spinner {
            border: 4px solid #333;
            border-top: 4px solid #e94560;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .species-section {
            margin-bottom: 30px;
        }

        .species-section.collapsed .species-groups {
            display: none;
        }

        .species-section.collapsed .species-header {
            border-radius: 10px;
        }

        .species-groups {
            transition: max-height 0.3s ease;
        }

        .species-header {
            background: #e94560;
            color: white;
            padding: 15px 20px;
            border-radius: 10px 10px 0 0;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            cursor: pointer;
            user-select: none;
            transition: border-radius 0.2s;
        }

        .species-header:hover {
            filter: brightness(1.1);
        }

        .species-header.confirmed {
            background: #2d8a6e;
        }

        .species-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .collapse-indicator {
            font-size: 14px;
            transition: transform 0.2s;
            display: inline-block;
            margin-right: 8px;
        }

        .species-section.collapsed .collapse-indicator {
            transform: rotate(-90deg);
        }

        .species-header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .species-stats {
            font-size: 14px;
            font-weight: normal;
            opacity: 0.9;
        }

        .duplicate-group {
            background: #16213e;
            border-radius: 10px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: border-color 0.2s;
            border: 2px solid transparent;
        }

        .duplicate-group.confirmed {
            border-color: #4ecca3;
        }

        .species-section .duplicate-group:first-of-type {
            border-radius: 0 0 10px 10px;
            margin-top: 0;
        }

        .species-section .duplicate-group {
            border-radius: 10px;
            margin-top: 10px;
        }

        .group-header {
            background: #0f3460;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            cursor: pointer;
            user-select: none;
        }

        .group-header:hover {
            background: #14477a;
        }

        .group-header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .group-collapse-indicator {
            font-size: 14px;
            transition: transform 0.2s;
            display: inline-block;
            margin-right: 5px;
        }

        .duplicate-group.collapsed .group-collapse-indicator {
            transform: rotate(-90deg);
        }

        .duplicate-group.collapsed .images-container {
            display: none;
        }

        .similar-group.collapsed .group-collapse-indicator {
            transform: rotate(-90deg);
        }

        .similar-group.collapsed .images-container {
            display: none;
        }

        .group-title {
            font-weight: bold;
            color: #e94560;
        }

        .group-count {
            background: #e94560;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
        }

        .images-container {
            display: flex;
            flex-wrap: wrap;
            padding: 15px;
            gap: 15px;
        }

        .image-card {
            background: #0f3460;
            border-radius: 8px;
            overflow: hidden;
            width: 250px;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .image-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
        }

        .image-card.keep {
            border: 3px solid #4ecca3;
        }

        .image-card.duplicate {
            border: 3px solid #e94560;
        }

        .image-wrapper {
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
            cursor: pointer;
            border: 3px solid #333;
            border-radius: 8px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .image-wrapper img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        /* Color-coding for detection types */
        .image-wrapper[data-type="duplicate"] {
            border-color: #dc3545;
        }

        .image-wrapper[data-type="cnn_similarity"] {
            border-color: #007bff;
        }

        .image-wrapper[data-type="outlier"] {
            border-color: #ffc107;
        }

        /* Selected for deletion state */
        .image-wrapper.selected-for-deletion {
            box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.5);
            border-color: #dc3545 !important;
        }

        .image-wrapper.selected-for-deletion::after {
            content: '✓';
            position: absolute;
            top: 10px;
            right: 10px;
            background: #dc3545;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
        }

        .image-info {
            padding: 10px;
        }

        .image-filename {
            font-size: 12px;
            color: #ddd;
            word-break: break-all;
            margin-bottom: 5px;
        }

        .image-size {
            font-size: 11px;
            color: #888;
        }

        .image-status {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            margin-top: 5px;
        }

        .status-keep {
            background: #4ecca3;
            color: #000;
        }

        .status-delete {
            background: #e94560;
            color: #fff;
        }

        .no-duplicates {
            text-align: center;
            padding: 50px;
            color: #4ecca3;
            font-size: 18px;
        }

        .error {
            background: #e94560;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .success-message {
            background: #4ecca3;
            color: #000;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: bold;
        }

        .warning-banner {
            background: #ff9800;
            color: #000;
            padding: 15px 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: bold;
            display: none;
            align-items: center;
            gap: 15px;
        }

        .warning-banner.active {
            display: flex;
        }

        .warning-icon {
            font-size: 24px;
        }

        .view-btn {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0, 123, 255, 0.9);
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            z-index: 10;
            transition: background 0.2s;
        }

        .view-btn:hover {
            background: rgba(0, 123, 255, 1);
        }

        .type-badge {
            position: absolute;
            top: 10px;
            left: 10px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            z-index: 10;
        }

        .type-badge.duplicate {
            background: #dc3545;
            color: white;
        }

        .type-badge.cnn_similarity {
            background: #007bff;
            color: white;
        }

        .type-badge.outlier {
            background: #ffc107;
            color: black;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .modal.active {
            display: flex;
        }

        .modal img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
        }

        .modal-close {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            color: white;
            cursor: pointer;
        }

        /* Confirmation modal */
        .confirm-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1001;
            justify-content: center;
            align-items: center;
        }

        .confirm-modal.active {
            display: flex;
        }

        .confirm-modal-content {
            background: #16213e;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }

        .confirm-modal-content h2 {
            color: #e94560;
            margin-bottom: 15px;
        }

        .confirm-modal-content p {
            margin-bottom: 20px;
            line-height: 1.6;
        }

        .confirm-modal-content .warning-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }

        .confirm-modal-content .file-count {
            font-size: 36px;
            font-weight: bold;
            color: #e94560;
            margin: 10px 0;
        }

        .confirm-modal-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
        }

        .confirm-modal-buttons button {
            min-width: 120px;
        }

        .threshold-info {
            background: #0f3460;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 12px;
            color: #aaa;
            margin-top: 10px;
        }

        .threshold-info strong {
            color: #e94560;
        }

        .warning-banner {
            background: #ff9800;
            color: #000;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: bold;
        }

        .checkmark {
            color: #4ecca3;
            margin-right: 5px;
        }

        .cache-controls {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .cache-controls button {
            font-size: 12px;
            padding: 5px 10px;
        }

        #cacheInfo {
            font-size: 12px;
            color: #888;
        }

        .cache-status {
            font-size: 12px;
            color: #4ecca3;
            margin-left: 10px;
        }

        .cache-status.from-cache {
            color: #4ecca3;
        }

        .cache-status.from-server {
            color: #ff9800;
        }

        /* CNN Similar Images Styles */
        .similar-section {
            margin-top: 30px;
            border-top: 3px dashed #ff9800;
            padding-top: 20px;
        }

        .similar-section-header {
            background: linear-gradient(135deg, #ff9800, #f57c00);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .similar-section-header h3 {
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .similar-badge {
            background: rgba(255,255,255,0.2);
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
        }

        .similar-group {
            background: #1a1a2e;
            border: 2px solid #ff9800;
            border-radius: 10px;
            margin-bottom: 20px;
            overflow: hidden;
        }

        .similar-group .group-header {
            background: linear-gradient(135deg, #2d2d44, #1a1a2e);
            border-bottom: 1px solid #ff9800;
        }

        .similar-group .group-title {
            color: #ff9800;
        }

        .similar-group .image-card {
            border: 2px solid #ff9800;
        }

        .similar-group .image-status {
            background: #ff9800;
            color: #000;
        }

        .cnn-controls {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .cnn-controls label {
            font-size: 12px;
            color: #aaa;
        }

        .cnn-controls input[type="range"] {
            width: 120px;
        }

        .cnn-controls .threshold-value {
            min-width: 40px;
            text-align: center;
            font-weight: bold;
            color: #ff9800;
        }

        .cnn-loading {
            text-align: center;
            padding: 30px;
            color: #ff9800;
            font-style: italic;
        }

        .cnn-unavailable {
            background: #333;
            color: #888;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-top: 20px;
        }

        .toggle-cnn {
            background: #ff9800;
            color: #000;
        }

        .toggle-cnn:hover {
            background: #ffb74d;
        }

        .toggle-cnn.active {
            background: #4ecca3;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌿 Duplicate Image Review</h1>
            <p>Visual review tool for tuning deduplication parameters</p>

            <div class="controls">
                <div class="control-group">
                    <label>Detection Type</label>
                    <div class="mode-buttons">
                        <button id="cnnModeBtn" class="secondary active" onclick="setDetectionMode('cnn')">CNN Similarity</button>
                        <button id="duplicateModeBtn" class="secondary" onclick="setDetectionMode('duplicate')">Direct Duplicates</button>
                        <button id="outlierModeBtn" class="secondary" onclick="setDetectionMode('outlier')">Outliers</button>
                        <button id="combinedModeBtn" class="secondary" onclick="setDetectionMode('combined')">Combined</button>
                    </div>
                </div>

                <div class="control-group">
                    <label>View Mode</label>
                    <div class="mode-buttons">
                        <button id="singleModeBtn" class="secondary active" onclick="setMode('single')">Single Species</button>
                        <button id="allModeBtn" class="secondary" onclick="setMode('all')">All Species</button>
                    </div>
                </div>

                <div class="control-group" id="speciesSelectGroup">
                    <label>Species</label>
                    <select id="speciesSelect">
                        <option value="">Loading species...</option>
                    </select>
                </div>

                <div class="control-group" id="hashSizeGroup">
                    <label>Hash Size</label>
                    <input type="number" id="hashSize" value="16" min="4" max="32" step="2">
                </div>

                <div class="control-group" id="hammingThresholdGroup">
                    <label>Hamming Threshold</label>
                    <input type="number" id="hammingThreshold" value="5" min="0" max="20">
                    <button class="secondary" style="padding: 5px 10px; font-size: 12px; margin-top: 5px;" onclick="updateHammingThreshold()">Update</button>
                </div>

                <div class="control-group" id="cnnThresholdGroup">
                    <label>CNN Threshold</label>
                    <input type="number" id="cnnThresholdInput" value="0.85" min="0.5" max="0.99" step="0.01">
                    <button class="secondary" style="padding: 5px 10px; font-size: 12px; margin-top: 5px;" onclick="updateCnnThreshold()">Update</button>
                </div>

                <div class="control-group" id="outlierSettingsGroup" style="display: none;">
                    <label>Outlier Thresholds</label>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <div>
                            <label style="font-size: 12px; color: #888;">Isolation Threshold:</label>
                            <input type="number" id="isolationThreshold" value="0.75" min="0.5" max="0.95" step="0.05" style="width: 70px;">
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #888;">Centroid Multiplier:</label>
                            <input type="number" id="centroidMultiplier" value="2.0" min="1.0" max="4.0" step="0.5" style="width: 70px;">
                        </div>
                    </div>
                </div>

                <div class="control-group">
                    <label>&nbsp;</label>
                    <button id="analyzeBtn" onclick="analyzeDuplicates()">Analyze</button>
                </div>
            </div>

            <div class="threshold-info" id="thresholdInfo">
                <strong>Hamming Threshold:</strong> Lower values = stricter matching (fewer false positives).
                Higher values = more permissive (may catch more duplicates but also false positives).
                <br>
                <strong>Hash Size:</strong> Higher values = more precise hashing but slower computation.
                <br>
                <strong>Cache:</strong> Image hashes are cached in your browser. Changing threshold uses cached data instantly.
            </div>
            <div class="threshold-info" id="outlierInfo" style="display: none;">
                <strong>Isolation Threshold:</strong> Images with max similarity to any other image below this value
                are flagged as "isolated". <em>Lower = more sensitive (more outliers). Higher = less sensitive.</em>
                <br>
                <strong>Centroid Multiplier:</strong> Images beyond (mean + X &times; std) distance from the species
                centroid are flagged as "distant". <em>Lower = more sensitive (more outliers). Higher = less sensitive.</em>
                <br>
                <strong>Tip:</strong> If seeing too many outliers, increase both values. Start with Centroid Multiplier = 2.5 or 3.0.
            </div>
            <div class="cache-controls">
                <button class="secondary" onclick="clearHashCache()">Clear Cache</button>
                <button class="toggle-cnn" id="cnnToggle" onclick="toggleCNN()">🧠 Enable CNN Similarity</button>
                <span id="cacheInfo">Cache: checking...</span>
                <span id="faissStatus" style="margin-left: 15px; font-size: 12px;"></span>
            </div>
            <div id="cnnControls" class="cnn-controls" style="display: none; margin-top: 10px;">
                <label>CNN Similarity Threshold:</label>
                <input type="range" id="cnnThreshold" min="0.5" max="0.99" step="0.01" value="0.85"
                       oninput="updateCnnThresholdDisplay()" onchange="updateCnnThresholdGroups()">
                <span class="threshold-value" id="cnnThresholdValue">0.85</span>
                <span style="font-size: 11px; color: #888;">(Higher = stricter matching)</span>
            </div>
        </header>

        <div class="warning-banner" id="warningBanner">
            <span class="warning-icon">⚠️</span>
            <div id="warningMessage"></div>
        </div>

        <div class="action-bar" id="actionBar" style="display: none;">
            <div class="action-bar-left">
                <span class="confirmed-count" id="confirmedCount">0 groups confirmed</span>
                <button class="confirm-btn" onclick="confirmAll()">✓ Confirm All</button>
                <button class="secondary" onclick="resetConfirmations()">Reset</button>
                <button class="secondary" onclick="collapseAllSpecies()">Collapse All Species</button>
                <button class="secondary" onclick="expandAllSpecies()">Expand All Species</button>
                <button class="secondary" onclick="collapseAllGroups()">Collapse All Groups</button>
                <button class="secondary" onclick="expandAllGroups()">Expand All Groups</button>
                <span class="cache-status" id="cacheStatus"></span>
            </div>
            <div class="action-bar-right">
                <button class="delete-btn" id="deleteBtn" onclick="showDeleteModal()" disabled>
                    🗑️ Delete Confirmed Duplicates
                </button>
            </div>
        </div>

        <div class="stats" id="stats" style="display: none;">
            <div class="stat" id="speciesScannedStat" style="display: none;">
                <div class="stat-value" id="speciesScanned">0</div>
                <div class="stat-label">Species Scanned</div>
            </div>
            <div class="stat" id="speciesWithDupsStat" style="display: none;">
                <div class="stat-value" id="speciesWithDups">0</div>
                <div class="stat-label">Species with Duplicates</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="totalImages">0</div>
                <div class="stat-label">Total Images</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="duplicateGroups">0</div>
                <div class="stat-label">Duplicate Groups</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="totalDuplicates">0</div>
                <div class="stat-label">Marked for Deletion</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="uniqueImages">0</div>
                <div class="stat-label">Unique Images</div>
            </div>
        </div>

        <div id="content">
            <div class="loading" id="initialMessage">
                <p>Select a species and click "Analyze" to begin reviewing duplicates.</p>
                <p style="margin-top: 10px; font-size: 14px; color: #666;">
                    Or switch to "All Species" mode to scan the entire dataset.
                </p>
            </div>
        </div>
    </div>

    <!-- Image preview modal -->
    <div class="modal" id="imageModal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="Full size image">
    </div>

    <!-- Confirm All modal -->
    <div class="confirm-modal" id="confirmAllModal">
        <div class="confirm-modal-content">
            <div class="warning-icon">⚠️</div>
            <h2>Confirm All Groups</h2>
            <p>You are about to confirm <strong id="confirmAllCount">0</strong> duplicate groups for deletion.</p>
            <p>This will mark <strong id="confirmAllFiles">0</strong> files for deletion.</p>
            <p style="color: #aaa; font-size: 14px;">Files will not be deleted until you click the delete button.</p>
            <div class="confirm-modal-buttons">
                <button class="secondary" onclick="hideConfirmAllModal()">Cancel</button>
                <button class="confirm-btn" onclick="doConfirmAll()">Confirm All</button>
            </div>
        </div>
    </div>

    <!-- Delete confirmation modal -->
    <div class="confirm-modal" id="deleteModal">
        <div class="confirm-modal-content">
            <div class="warning-icon">🗑️</div>
            <h2>Delete Confirmed Duplicates</h2>
            <p style="color: #e94560; font-weight: bold;">This action cannot be undone!</p>
            <div class="file-count" id="deleteFileCount">0</div>
            <p>files will be permanently deleted</p>
            <p style="color: #aaa; font-size: 14px; margin-top: 15px;">
                Only files in confirmed groups will be deleted.<br>
                The highest quality image from each group will be kept.
            </p>
            <div class="confirm-modal-buttons">
                <button class="secondary" onclick="hideDeleteModal()">Cancel</button>
                <button class="delete-btn" onclick="executeDelete()">Delete Files</button>
            </div>
        </div>
    </div>

    <script>
        let currentMode = 'single';
        let currentDetectionMode = 'cnn'; // 'cnn', 'duplicate', 'outlier', 'combined'
        let currentData = null;
        let confirmedGroups = new Set(); // Format: "speciesName:groupId"
        let selectedImages = new Set(); // Format: "species/filename"
        let cnnEnabled = false;
        let cnnData = null;
        const CACHE_PREFIX = 'plantnet_hashes_';
        const CNN_CACHE_PREFIX = 'plantnet_cnn_';
        const CACHE_VERSION = 'v1';

        // Check FAISS vector database availability
        async function checkFaissStatus() {
            try {
                const response = await fetch('/api/faiss/status');
                const data = await response.json();

                const statusEl = document.getElementById('faissStatus');
                if (data.available) {
                    statusEl.innerHTML = '⚡ <span style="color: #4ecca3;">Vector DB Ready</span>';
                    statusEl.title = `${data.count} pre-computed embeddings`;
                } else {
                    statusEl.innerHTML = '⚠️ <span style="color: #ff9800;">On-demand mode</span>';
                    statusEl.title = 'Run batch_generate_embeddings.py to enable vector search';
                }
            } catch (e) {
                console.warn('Could not check FAISS status:', e);
            }
        }

        // Load species list on page load
        document.addEventListener('DOMContentLoaded', () => {
            loadSpecies();
            updateCacheInfo();
            updateCnnThresholdDisplay();
            checkFaissStatus();
            updateControlVisibility();
        });

        // ==================== Detection Mode Functions ====================

        function setDetectionMode(mode) {
            currentDetectionMode = mode;

            // Update button states
            document.getElementById('cnnModeBtn').classList.toggle('active', mode === 'cnn');
            document.getElementById('duplicateModeBtn').classList.toggle('active', mode === 'duplicate');
            document.getElementById('outlierModeBtn').classList.toggle('active', mode === 'outlier');
            document.getElementById('combinedModeBtn').classList.toggle('active', mode === 'combined');

            // Update control visibility
            updateControlVisibility();

            // Clear current results
            document.getElementById('content').innerHTML = '<div class="loading"><p>Select settings and click Analyze to view ' + mode + ' detection results.</p></div>';
        }

        function updateControlVisibility() {
            const mode = currentDetectionMode;
            const hashSizeGroup = document.getElementById('hashSizeGroup');
            const hammingGroup = document.getElementById('hammingThresholdGroup');
            const cnnGroup = document.getElementById('cnnThresholdGroup');
            const outlierGroup = document.getElementById('outlierSettingsGroup');
            const thresholdInfo = document.getElementById('thresholdInfo');
            const outlierInfo = document.getElementById('outlierInfo');

            // Show/hide controls based on detection mode
            if (mode === 'duplicate') {
                hashSizeGroup.style.display = 'flex';
                hammingGroup.style.display = 'flex';
                cnnGroup.style.display = 'none';
                outlierGroup.style.display = 'none';
                thresholdInfo.style.display = 'block';
                outlierInfo.style.display = 'none';
            } else if (mode === 'cnn') {
                hashSizeGroup.style.display = 'none';
                hammingGroup.style.display = 'none';
                cnnGroup.style.display = 'flex';
                outlierGroup.style.display = 'none';
                thresholdInfo.style.display = 'block';
                outlierInfo.style.display = 'none';
            } else if (mode === 'outlier') {
                hashSizeGroup.style.display = 'none';
                hammingGroup.style.display = 'none';
                cnnGroup.style.display = 'none';
                outlierGroup.style.display = 'flex';
                thresholdInfo.style.display = 'none';
                outlierInfo.style.display = 'block';
            } else if (mode === 'combined') {
                hashSizeGroup.style.display = 'flex';
                hammingGroup.style.display = 'flex';
                cnnGroup.style.display = 'flex';
                outlierGroup.style.display = 'flex';
                thresholdInfo.style.display = 'block';
                outlierInfo.style.display = 'block';
            }
        }

        function updateCnnThreshold() {
            if (!currentData) return;
            analyzeDuplicates();
        }

        function updateHammingThreshold() {
            if (!currentData) return;
            analyzeDuplicates();
        }

        // ==================== CNN Toggle Functions ====================

        function toggleCNN() {
            cnnEnabled = !cnnEnabled;
            const btn = document.getElementById('cnnToggle');
            const controls = document.getElementById('cnnControls');

            if (cnnEnabled) {
                btn.textContent = '🧠 CNN Similarity ON';
                btn.classList.add('active');
                controls.style.display = 'flex';
            } else {
                btn.textContent = '🧠 Enable CNN Similarity';
                btn.classList.remove('active');
                controls.style.display = 'none';
            }
        }

        function updateCnnThresholdDisplay() {
            const value = document.getElementById('cnnThreshold').value;
            document.getElementById('cnnThresholdValue').textContent = value;
        }

        function updateCnnThresholdGroups() {
            if (!currentData || currentMode !== 'single') return;
            if (!cnnEnabled) return;

            const speciesName = currentData.species_results[0]?.species_name;
            if (!speciesName) return;

            const threshold = parseFloat(document.getElementById('cnnThreshold').value);
            const cachedCnn = getCachedCnnEmbeddings(speciesName);

            if (cachedCnn) {
                // Re-group with new threshold using cached data
                const result = processWithCachedCnnEmbeddings(speciesName, cachedCnn, threshold);
                displayCnnResults(result);
                setCacheStatus(true);
            }
        }

        function getCnnCacheKey(speciesName) {
            return `${CNN_CACHE_PREFIX}${CACHE_VERSION}_${speciesName}`;
        }

        function getCachedCnnEmbeddings(speciesName) {
            try {
                const key = getCnnCacheKey(speciesName);
                const data = localStorage.getItem(key);
                if (data) {
                    return JSON.parse(data);
                }
            } catch (e) {
                console.warn('Failed to read CNN cache:', e);
            }
            return null;
        }

        function setCachedCnnEmbeddings(speciesName, images) {
            try {
                const key = getCnnCacheKey(speciesName);
                const cacheData = {
                    timestamp: Date.now(),
                    images: images
                };
                localStorage.setItem(key, JSON.stringify(cacheData));
            } catch (e) {
                console.warn('Failed to write CNN cache:', e);
            }
        }

        // ==================== LocalStorage Cache Functions ====================

        function getCacheKey(speciesName, hashSize) {
            return `${CACHE_PREFIX}${CACHE_VERSION}_${speciesName}_${hashSize}`;
        }

        function getCachedHashes(speciesName, hashSize) {
            try {
                const key = getCacheKey(speciesName, hashSize);
                const data = localStorage.getItem(key);
                if (data) {
                    return JSON.parse(data);
                }
            } catch (e) {
                console.warn('Failed to read from cache:', e);
            }
            return null;
        }

        function setCachedHashes(speciesName, hashSize, images) {
            try {
                const key = getCacheKey(speciesName, hashSize);
                const cacheData = {
                    timestamp: Date.now(),
                    images: images
                };
                localStorage.setItem(key, JSON.stringify(cacheData));
            } catch (e) {
                console.warn('Failed to write to cache:', e);
            }
        }

        function clearHashCache() {
            const keys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && (key.startsWith(CACHE_PREFIX) || key.startsWith(CNN_CACHE_PREFIX))) {
                    keys.push(key);
                }
            }
            keys.forEach(key => localStorage.removeItem(key));
            updateCacheInfo();
            alert(`Cleared ${keys.length} cached entries (hashes + CNN embeddings)`);
        }

        function updateCacheInfo() {
            let hashCount = 0;
            let cnnCount = 0;
            let totalSize = 0;
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith(CACHE_PREFIX)) {
                    hashCount++;
                    totalSize += localStorage.getItem(key).length;
                } else if (key && key.startsWith(CNN_CACHE_PREFIX)) {
                    cnnCount++;
                    totalSize += localStorage.getItem(key).length;
                }
            }
            const sizeKB = (totalSize / 1024).toFixed(1);
            const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
            const sizeStr = totalSize > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;
            document.getElementById('cacheInfo').textContent =
                `Cache: ${hashCount} hash + ${cnnCount} CNN (${sizeStr})`;
        }

        function setCacheStatus(fromCache, speciesCount = 1) {
            const el = document.getElementById('cacheStatus');
            if (fromCache) {
                el.textContent = `⚡ Loaded from cache`;
                el.className = 'cache-status from-cache';
            } else {
                el.textContent = `📡 Fetched from server`;
                el.className = 'cache-status from-server';
            }
        }

        // ==================== Client-side Duplicate Grouping ====================

        function hammingDistance(hash1, hash2) {
            if (!hash1 || !hash2 || hash1.length !== hash2.length) {
                return Infinity;
            }
            let distance = 0;
            for (let i = 0; i < hash1.length; i++) {
                const diff = parseInt(hash1[i], 16) ^ parseInt(hash2[i], 16);
                distance += (diff & 1) + ((diff >> 1) & 1) + ((diff >> 2) & 1) + ((diff >> 3) & 1);
            }
            return distance;
        }

        function findDuplicateGroupsClient(images, threshold) {
            const validImages = images.filter(img => img.hash);
            const n = validImages.length;
            if (n < 2) return [];

            // Union-Find
            const parent = Array.from({length: n}, (_, i) => i);
            const rank = new Array(n).fill(0);

            function find(x) {
                if (parent[x] !== x) parent[x] = find(parent[x]);
                return parent[x];
            }

            function union(x, y) {
                const px = find(x), py = find(y);
                if (px === py) return;
                if (rank[px] < rank[py]) {
                    parent[px] = py;
                } else if (rank[px] > rank[py]) {
                    parent[py] = px;
                } else {
                    parent[py] = px;
                    rank[px]++;
                }
            }

            // Compare all pairs
            for (let i = 0; i < n; i++) {
                for (let j = i + 1; j < n; j++) {
                    const dist = hammingDistance(validImages[i].hash, validImages[j].hash);
                    if (dist <= threshold) {
                        union(i, j);
                    }
                }
            }

            // Group by root
            const groups = new Map();
            for (let i = 0; i < n; i++) {
                const root = find(i);
                if (!groups.has(root)) groups.set(root, []);
                groups.get(root).push(validImages[i]);
            }

            // Filter to groups with duplicates and format
            const result = [];
            let groupId = 1;
            for (const [_, group] of groups) {
                if (group.length > 1) {
                    // Sort by size descending, then name
                    group.sort((a, b) => b.size - a.size || a.filename.localeCompare(b.filename));
                    const keep = group[0];
                    const duplicates = group.slice(1);
                    result.push({
                        group_id: groupId++,
                        keep: keep,
                        duplicates: duplicates,
                        total_in_group: group.length
                    });
                }
            }
            return result;
        }

        function processWithCachedHashes(speciesName, cachedData, hashSize, threshold) {
            const images = cachedData.images;
            const duplicateGroups = findDuplicateGroupsClient(images, threshold);
            const totalDuplicates = duplicateGroups.reduce((sum, g) => sum + g.duplicates.length, 0);

            return {
                species_name: speciesName,
                total_images: images.length,
                hashed_images: images.filter(img => img.hash).length,
                duplicate_groups: duplicateGroups,
                total_duplicates: totalDuplicates,
                hash_size: hashSize,
                hamming_threshold: threshold,
                images: images,
                from_cache: true
            };
        }

        // ==================== Client-side CNN Grouping ====================

        function cosineSimilarity(vec1, vec2) {
            if (!vec1 || !vec2 || vec1.length !== vec2.length) {
                return 0;
            }
            let dot = 0, normA = 0, normB = 0;
            for (let i = 0; i < vec1.length; i++) {
                dot += vec1[i] * vec2[i];
                normA += vec1[i] * vec1[i];
                normB += vec2[i] * vec2[i];
            }
            if (normA === 0 || normB === 0) return 0;
            return dot / (Math.sqrt(normA) * Math.sqrt(normB));
        }

        function findCnnSimilarGroupsClient(images, threshold) {
            const validImages = images.filter(img => img.embedding);
            const n = validImages.length;
            if (n < 2) return [];

            // Union-Find
            const parent = Array.from({length: n}, (_, i) => i);
            const rank = new Array(n).fill(0);

            function find(x) {
                if (parent[x] !== x) parent[x] = find(parent[x]);
                return parent[x];
            }

            function union(x, y) {
                const px = find(x), py = find(y);
                if (px === py) return;
                if (rank[px] < rank[py]) {
                    parent[px] = py;
                } else if (rank[px] > rank[py]) {
                    parent[py] = px;
                } else {
                    parent[py] = px;
                    rank[px]++;
                }
            }

            // Compare all pairs
            for (let i = 0; i < n; i++) {
                for (let j = i + 1; j < n; j++) {
                    const sim = cosineSimilarity(validImages[i].embedding, validImages[j].embedding);
                    if (sim >= threshold) {
                        union(i, j);
                    }
                }
            }

            // Group by root
            const groups = new Map();
            for (let i = 0; i < n; i++) {
                const root = find(i);
                if (!groups.has(root)) groups.set(root, []);
                groups.get(root).push(validImages[i]);
            }

            // Filter to groups with multiple images and format
            const result = [];
            let groupId = 1;
            for (const [_, group] of groups) {
                if (group.length > 1) {
                    // Sort by size descending, then name
                    group.sort((a, b) => b.size - a.size || a.filename.localeCompare(b.filename));
                    result.push({
                        group_id: groupId++,
                        images: group.map(img => ({
                            filename: img.filename,
                            size: img.size,
                            path: img.path
                        })),
                        count: group.length
                    });
                }
            }
            return result;
        }

        function processWithCachedCnnEmbeddings(speciesName, cachedData, threshold) {
            const images = cachedData.images;
            const similarGroups = findCnnSimilarGroupsClient(images, threshold);
            const totalInGroups = similarGroups.reduce((sum, g) => sum + g.count, 0);

            return {
                species_name: speciesName,
                total_images: images.length,
                processed_images: images.filter(img => img.embedding).length,
                similar_groups: similarGroups,
                total_in_groups: totalInGroups,
                similarity_threshold: threshold,
                images: images,
                from_cache: true
            };
        }

        function setMode(mode) {
            currentMode = mode;
            confirmedGroups.clear();
            updateConfirmedCount();

            document.getElementById('singleModeBtn').classList.toggle('active', mode === 'single');
            document.getElementById('allModeBtn').classList.toggle('active', mode === 'all');
            document.getElementById('speciesSelectGroup').style.display = mode === 'single' ? 'flex' : 'none';

            if (mode === 'all') {
                document.getElementById('initialMessage').innerHTML = `
                    <p>Click "Analyze" to scan ALL species for duplicates.</p>
                    <p style="margin-top: 10px; font-size: 14px; color: #ff9800;">
                        ⚠️ This may take several minutes depending on the number of species and images.
                    </p>
                `;
            } else {
                document.getElementById('initialMessage').innerHTML = `
                    <p>Select a species and click "Analyze" to begin reviewing duplicates.</p>
                    <p style="margin-top: 10px; font-size: 14px; color: #666;">
                        Or switch to "All Species" mode to scan the entire dataset.
                    </p>
                `;
            }
        }

        async function loadSpecies() {
            try {
                const response = await fetch('/api/species');
                const species = await response.json();

                const select = document.getElementById('speciesSelect');
                select.innerHTML = '<option value="">-- Select a species --</option>';

                species.forEach(name => {
                    const option = document.createElement('option');
                    option.value = name;
                    option.textContent = name.replace(/_/g, ' ');
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Failed to load species:', error);
                document.getElementById('speciesSelect').innerHTML =
                    '<option value="">Error loading species</option>';
            }
        }

        async function analyzeDuplicates() {
            confirmedGroups.clear();
            selectedImages.clear();
            updateConfirmedCount();

            if (currentMode === 'single') {
                await analyzeSingleSpecies();
            } else {
                await analyzeAllSpecies();
            }
        }

        async function analyzeSingleSpecies() {
            const species = document.getElementById('speciesSelect').value;
            if (!species) {
                alert('Please select a species first');
                return;
            }

            document.getElementById('stats').style.display = 'none';
            document.getElementById('actionBar').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;

            const mode = currentDetectionMode;

            try {
                let data;
                let apiUrl;
                const hashSize = parseInt(document.getElementById('hashSize').value);
                const hammingThreshold = parseInt(document.getElementById('hammingThreshold').value);
                const cnnThreshold = parseFloat(document.getElementById('cnnThresholdInput').value);
                const isolationThreshold = parseFloat(document.getElementById('isolationThreshold').value) || 0.75;
                const centroidMultiplier = parseFloat(document.getElementById('centroidMultiplier').value) || 2.0;

                // Determine API endpoint based on detection mode
                if (mode === 'cnn') {
                    apiUrl = `/api/similarity/${species}?threshold=${cnnThreshold}`;
                    document.getElementById('content').innerHTML = `
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Computing CNN similarity for ${species.replace(/_/g, ' ')}...</p>
                        </div>
                    `;
                } else if (mode === 'duplicate') {
                    apiUrl = `/api/duplicates/${species}?hash_size=${hashSize}&threshold=${hammingThreshold}`;
                    document.getElementById('content').innerHTML = `
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Finding duplicates for ${species.replace(/_/g, ' ')}...</p>
                        </div>
                    `;
                } else if (mode === 'outlier') {
                    apiUrl = `/api/outliers/${species}?threshold=${isolationThreshold}&centroid_multiplier=${centroidMultiplier}`;
                    document.getElementById('content').innerHTML = `
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Detecting outliers for ${species.replace(/_/g, ' ')}...</p>
                        </div>
                    `;
                } else if (mode === 'combined') {
                    apiUrl = `/api/combined/${species}?similarity_threshold=${cnnThreshold}&hamming_threshold=${hammingThreshold}&hash_size=${hashSize}&outlier_isolation_threshold=${isolationThreshold}&outlier_centroid_multiplier=${centroidMultiplier}`;
                    document.getElementById('content').innerHTML = `
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Running combined analysis for ${species.replace(/_/g, ' ')}...</p>
                        </div>
                    `;
                }

                const response = await fetch(apiUrl);
                data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                currentData = data;

                // Display results based on mode
                if (mode === 'cnn') {
                    displayCnnResults(data);
                } else if (mode === 'duplicate') {
                    displayDuplicateResults(data);
                } else if (mode === 'outlier') {
                    displayOutlierResults(data);
                } else if (mode === 'combined') {
                    displayCombinedResults(data);
                }

                document.getElementById('stats').style.display = 'flex';
                document.getElementById('actionBar').style.display = 'flex';
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            } finally {
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        async function analyzeAllSpecies() {
            const hashSize = parseInt(document.getElementById('hashSize').value);
            const threshold = parseInt(document.getElementById('hammingThreshold').value);

            document.getElementById('stats').style.display = 'none';
            document.getElementById('actionBar').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;

            // Get species list first
            let speciesList;
            try {
                const response = await fetch('/api/species');
                speciesList = await response.json();
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> Failed to load species list</div>
                `;
                document.getElementById('analyzeBtn').disabled = false;
                return;
            }

            // Check which species are cached
            const cachedSpecies = [];
            const uncachedSpecies = [];
            for (const species of speciesList) {
                if (getCachedHashes(species, hashSize)) {
                    cachedSpecies.push(species);
                } else {
                    uncachedSpecies.push(species);
                }
            }

            document.getElementById('content').innerHTML = `
                <div class="warning-banner">
                    ⚠️ Scanning ${speciesList.length} species
                    (${cachedSpecies.length} cached, ${uncachedSpecies.length} to fetch)
                </div>
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing images across all species...</p>
                    <p id="progressText" style="font-size: 12px; margin-top: 10px;">Initializing...</p>
                </div>
            `;

            try {
                const allResults = [];
                let totalImages = 0;
                let totalDuplicates = 0;
                let totalGroups = 0;
                let speciesWithDuplicates = 0;
                let processed = 0;

                // Process cached species first (fast)
                for (const species of cachedSpecies) {
                    const cachedData = getCachedHashes(species, hashSize);
                    const data = processWithCachedHashes(species, cachedData, hashSize, threshold);

                    totalImages += data.total_images;
                    if (data.total_duplicates > 0) {
                        totalDuplicates += data.total_duplicates;
                        totalGroups += data.duplicate_groups.length;
                        speciesWithDuplicates++;
                        allResults.push(data);
                    }
                    processed++;
                    document.getElementById('progressText').textContent =
                        `Processing: ${processed}/${speciesList.length} (${species})`;
                }

                // Fetch uncached species from server
                for (const species of uncachedSpecies) {
                    document.getElementById('progressText').textContent =
                        `Fetching: ${processed + 1}/${speciesList.length} (${species})`;

                    const response = await fetch(
                        `/api/duplicates/${species}?hash_size=${hashSize}&threshold=${threshold}`
                    );
                    const data = await response.json();

                    if (!data.error) {
                        // Cache for future use
                        if (data.images && data.images.length > 0) {
                            setCachedHashes(species, hashSize, data.images);
                        }

                        totalImages += data.total_images;
                        if (data.total_duplicates > 0) {
                            totalDuplicates += data.total_duplicates;
                            totalGroups += data.duplicate_groups.length;
                            speciesWithDuplicates++;
                            allResults.push(data);
                        }
                    }
                    processed++;
                }

                updateCacheInfo();

                const finalData = {
                    mode: 'all_species',
                    total_species_scanned: speciesList.length,
                    species_with_duplicates: speciesWithDuplicates,
                    total_images: totalImages,
                    total_duplicates: totalDuplicates,
                    total_groups: totalGroups,
                    hash_size: hashSize,
                    hamming_threshold: threshold,
                    species_results: allResults,
                };

                currentData = finalData;
                displayAllSpeciesResults(finalData);
                setCacheStatus(uncachedSpecies.length === 0, speciesList.length);

                // CNN similarity for all species mode is not supported yet
                if (cnnEnabled) {
                    appendCnnNotice('CNN similarity in "All Species" mode requires analyzing each species individually.');
                }
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            } finally {
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        function displaySingleSpeciesResults(data) {
            document.getElementById('speciesScannedStat').style.display = 'none';
            document.getElementById('speciesWithDupsStat').style.display = 'none';
            document.getElementById('stats').style.display = 'flex';
            document.getElementById('totalImages').textContent = data.total_images;
            document.getElementById('duplicateGroups').textContent = data.duplicate_groups.length;
            document.getElementById('totalDuplicates').textContent = data.total_duplicates;
            document.getElementById('uniqueImages').textContent = data.total_images - data.total_duplicates;

            const content = document.getElementById('content');

            if (data.duplicate_groups.length === 0) {
                document.getElementById('actionBar').style.display = 'none';
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No duplicate images found with current settings.<br>
                        <small>Try increasing the Hamming threshold to detect more similar images.</small>
                    </div>
                `;
                return;
            }

            document.getElementById('actionBar').style.display = 'flex';
            let html = '';
            data.duplicate_groups.forEach(group => {
                html += renderDuplicateGroup(data.species_name, group);
            });
            content.innerHTML = html;

            // Add CNN section placeholder
            if (cnnEnabled) {
                const cnnSection = document.createElement('div');
                cnnSection.id = 'cnnSimilaritySection';
                cnnSection.innerHTML = '<div class="cnn-loading">🧠 CNN similarity analysis will appear here...</div>';
                document.getElementById('content').appendChild(cnnSection);
            }
        }

        async function fetchCnnSimilarity(speciesName) {
            const threshold = parseFloat(document.getElementById('cnnThreshold').value);

            // Check localStorage cache first
            const cachedCnn = getCachedCnnEmbeddings(speciesName);
            if (cachedCnn) {
                const result = processWithCachedCnnEmbeddings(speciesName, cachedCnn, threshold);
                displayCnnResults(result);
                setCacheStatus(true);
                return;
            }

            // Show loading in CNN section
            let cnnSection = document.getElementById('cnnSimilaritySection');
            if (!cnnSection) {
                cnnSection = document.createElement('div');
                cnnSection.id = 'cnnSimilaritySection';
                document.getElementById('content').appendChild(cnnSection);
            }
            cnnSection.innerHTML = `
                <div class="similar-section">
                    <div class="cnn-loading">
                        <div class="spinner"></div>
                        <p>🧠 Computing CNN embeddings for similarity analysis...</p>
                        <p style="font-size: 12px;">This may take a moment (using ResNet18)</p>
                    </div>
                </div>
            `;

            try {
                const response = await fetch(
                    `/api/similarity/${speciesName}?threshold=${threshold}`
                );
                const data = await response.json();

                if (data.error) {
                    cnnSection.innerHTML = `<div class="cnn-unavailable">⚠️ ${data.error}</div>`;
                    return;
                }

                // Cache embeddings to localStorage
                if (data.images && data.images.length > 0) {
                    setCachedCnnEmbeddings(speciesName, data.images);
                    updateCacheInfo();
                }

                displayCnnResults(data);
                setCacheStatus(false);
            } catch (error) {
                cnnSection.innerHTML = `<div class="cnn-unavailable">⚠️ Error: ${error.message}</div>`;
            }
        }

        function displayCnnResults(data) {
            let cnnSection = document.getElementById('cnnSimilaritySection');
            if (!cnnSection) {
                cnnSection = document.createElement('div');
                cnnSection.id = 'cnnSimilaritySection';
                document.getElementById('content').appendChild(cnnSection);
            }

            if (!data.similar_groups || data.similar_groups.length === 0) {
                cnnSection.innerHTML = `
                    <div class="similar-section">
                        <div class="similar-section-header">
                            <h3>🧠 CNN Similar Images</h3>
                            <span class="similar-badge">No similar images found at threshold ${data.similarity_threshold || 0.85}</span>
                        </div>
                        <p style="text-align: center; color: #888; padding: 20px;">
                            No semantically similar images detected. Try lowering the similarity threshold.
                        </p>
                    </div>
                `;
                return;
            }

            let html = `
                <div class="similar-section">
                    <div class="similar-section-header">
                        <h3>🧠 CNN Similar Images</h3>
                        <div>
                            <span class="similar-badge">${data.similar_groups.length} groups</span>
                            <span class="similar-badge">${data.total_in_groups} images</span>
                            <span class="similar-badge">Threshold: ${data.similarity_threshold || 0.85}</span>
                        </div>
                    </div>
                    <p style="color: #ff9800; font-size: 13px; margin-bottom: 15px; padding: 0 10px;">
                        ⚠️ These images are <strong>semantically similar</strong> (same subject, different shots) - not exact duplicates.
                        Review carefully before considering removal.
                    </p>
            `;

            data.similar_groups.forEach(group => {
                const groupId = `cnn-${data.species_name}-${group.group_id}`;
                html += `
                    <div class="similar-group" id="group-${groupId}">
                        <div class="group-header" onclick="toggleCnnGroupCollapse('${groupId}')">
                            <div class="group-header-left">
                                <span class="group-collapse-indicator">▼</span>
                                <span class="group-title">Similar Group ${group.group_id}</span>
                                <span class="group-count">${group.count} images</span>
                            </div>
                        </div>
                        <div class="images-container">
                            ${group.images.map(img => renderImageCard(img, 'cnn_similarity', data.species_name)).join('')}
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            cnnSection.innerHTML = html;
        }

        // Helper function to render image card with new behavior
        function renderImageCard(img, type, speciesName) {
            const imageKey = `${speciesName}/${img.filename}`;
            const selected = selectedImages.has(imageKey);
            return `
                <div class="image-card">
                    <div class="image-wrapper ${selected ? 'selected-for-deletion' : ''}"
                         data-type="${type}"
                         data-image-key="${imageKey}"
                         onclick="toggleImageSelection('${imageKey}')">
                        <span class="type-badge ${type}">${type.replace('_', ' ')}</span>
                        <img src="${img.path}" alt="${img.filename}" loading="lazy">
                        <button class="view-btn" onclick="event.stopPropagation(); showModal('${img.path}')">View</button>
                    </div>
                    <div class="image-info">
                        <div class="image-filename">${img.filename}</div>
                        <div class="image-size">${formatSize(img.size)}</div>
                    </div>
                </div>
            `;
        }

        // Toggle image selection for deletion
        function toggleImageSelection(imageKey) {
            if (selectedImages.has(imageKey)) {
                selectedImages.delete(imageKey);
            } else {
                selectedImages.add(imageKey);
            }

            // Update UI
            const wrapper = document.querySelector(`[data-image-key="${imageKey}"]`);
            if (wrapper) {
                wrapper.classList.toggle('selected-for-deletion');
            }

            updateDeleteButtonState();
            checkGroupDeletionWarning();
        }

        function updateDeleteButtonState() {
            const deleteBtn = document.getElementById('deleteBtn');
            if (selectedImages.size > 0) {
                deleteBtn.disabled = false;
                deleteBtn.textContent = `🗑️ Delete ${selectedImages.size} Selected Image${selectedImages.size > 1 ? 's' : ''}`;
            } else {
                deleteBtn.disabled = true;
                deleteBtn.textContent = '🗑️ Delete Selected Images';
            }
        }

        function checkGroupDeletionWarning() {
            // Check if any group has all images selected
            const warningBanner = document.getElementById('warningBanner');
            const warningMessage = document.getElementById('warningMessage');

            let hasFullGroupDeletion = false;
            let warningText = '';

            if (currentData && currentData.items) {
                // Combined view
                for (const item of currentData.items) {
                    const allSelected = item.images.every(img =>
                        selectedImages.has(`${currentData.species_name}/${img.filename}`)
                    );
                    if (allSelected && item.images.length > 1) {
                        hasFullGroupDeletion = true;
                        warningText = `Warning: All images in one or more groups are selected for deletion. Consider keeping at least one image from each group.`;
                        break;
                    }
                }
            }

            if (hasFullGroupDeletion) {
                warningBanner.classList.add('active');
                warningMessage.textContent = warningText;
            } else {
                warningBanner.classList.remove('active');
            }
        }

        function displayDuplicateResults(data) {
            const content = document.getElementById('content');
            if (!data.duplicate_groups || data.duplicate_groups.length === 0) {
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No duplicates found for ${data.species_name.replace(/_/g, ' ')}
                    </div>
                `;
                return;
            }

            let html = '<div class="results-container">';
            data.duplicate_groups.forEach(group => {
                html += `
                    <div class="duplicate-group">
                        <div class="group-header">
                            <div class="group-header-left">
                                <span class="group-title">Duplicate Group ${group.group_id}</span>
                                <span class="group-count">${group.total_in_group} images</span>
                            </div>
                        </div>
                        <div class="images-container">
                            ${renderImageCard(group.keep, 'duplicate', data.species_name)}
                            ${group.duplicates.map(dup => renderImageCard(dup, 'duplicate', data.species_name)).join('')}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            content.innerHTML = html;
        }

        function displayOutlierResults(data) {
            const content = document.getElementById('content');
            if (!data.outliers || data.outliers.length === 0) {
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No outliers found for ${data.species_name.replace(/_/g, ' ')}
                    </div>
                `;
                return;
            }

            let html = `
                <div class="results-container">
                    <div class="info-banner" style="background: #ffc107; color: #000; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                        <strong>Outlier Detection:</strong> Found ${data.outliers.length} images that are significantly different from other images in this species.
                        These may be misclassified images or unusual specimens.
                    </div>
            `;

            data.outliers.forEach((outlier, idx) => {
                html += `
                    <div class="duplicate-group">
                        <div class="group-header">
                            <div class="group-header-left">
                                <span class="group-title">Outlier ${idx + 1}</span>
                                <span class="group-count">${outlier.outlier_types.join(', ')}</span>
                            </div>
                        </div>
                        <div class="images-container">
                            ${renderImageCard(outlier, 'outlier', data.species_name)}
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            content.innerHTML = html;
        }

        function displayCombinedResults(data) {
            const content = document.getElementById('content');
            if (!data.items || data.items.length === 0) {
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No issues found for ${data.species_name.replace(/_/g, ' ')}
                    </div>
                `;
                return;
            }

            let html = `
                <div class="results-container">
                    <div class="info-banner" style="background: #007bff; color: #fff; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                        <strong>Combined View:</strong> Showing ${data.total_items} groups across all detection types.
                        Colors indicate type: <span style="color: #dc3545;">■</span> Duplicates,
                        <span style="color: #007bff;">■</span> CNN Similar,
                        <span style="color: #ffc107;">■</span> Outliers
                    </div>
            `;

            data.items.forEach((item, idx) => {
                const typeLabel = item.type === 'cnn_similarity' ? 'CNN Similar' :
                                 item.type === 'duplicate' ? 'Duplicate' : 'Outlier';
                html += `
                    <div class="duplicate-group">
                        <div class="group-header">
                            <div class="group-header-left">
                                <span class="group-title">${typeLabel} Group ${item.group_id}</span>
                                <span class="group-count">${item.count} image${item.count > 1 ? 's' : ''}</span>
                            </div>
                        </div>
                        <div class="images-container">
                            ${item.images.map(img => renderImageCard(img, item.type, data.species_name)).join('')}
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            content.innerHTML = html;
            updateDeleteButtonState();
            checkGroupDeletionWarning();
        }

        function appendCnnNotice(message) {
            let cnnSection = document.getElementById('cnnSimilaritySection');
            if (!cnnSection) {
                cnnSection = document.createElement('div');
                cnnSection.id = 'cnnSimilaritySection';
                document.getElementById('content').appendChild(cnnSection);
            }
            cnnSection.innerHTML = `
                <div class="similar-section">
                    <div class="cnn-unavailable">🧠 ${message}</div>
                </div>
            `;
        }

        function displayAllSpeciesResults(data) {
            document.getElementById('speciesScannedStat').style.display = 'block';
            document.getElementById('speciesWithDupsStat').style.display = 'block';
            document.getElementById('stats').style.display = 'flex';
            document.getElementById('speciesScanned').textContent = data.total_species_scanned;
            document.getElementById('speciesWithDups').textContent = data.species_with_duplicates;
            document.getElementById('totalImages').textContent = data.total_images;
            document.getElementById('duplicateGroups').textContent = data.total_groups;
            document.getElementById('totalDuplicates').textContent = data.total_duplicates;
            document.getElementById('uniqueImages').textContent = data.total_images - data.total_duplicates;

            const content = document.getElementById('content');

            if (data.species_results.length === 0) {
                document.getElementById('actionBar').style.display = 'none';
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No duplicate images found across any species with current settings.<br>
                        <small>Try increasing the Hamming threshold to detect more similar images.</small>
                    </div>
                `;
                return;
            }

            document.getElementById('actionBar').style.display = 'flex';
            let html = '';
            data.species_results.forEach(speciesData => {
                const speciesKey = speciesData.species_name;
                const allConfirmed = speciesData.duplicate_groups.every(g =>
                    confirmedGroups.has(`${speciesKey}:${g.group_id}`)
                );
                html += `
                    <div class="species-section" id="species-${speciesKey}">
                        <div class="species-header ${allConfirmed ? 'confirmed' : ''}" id="species-header-${speciesKey}" onclick="toggleSpeciesCollapse('${speciesKey}')">
                            <div class="species-header-left">
                                <span><span class="collapse-indicator">▼</span>${allConfirmed ? '<span class="checkmark">✓</span>' : ''}🌿 ${speciesData.species_name.replace(/_/g, ' ')}</span>
                            </div>
                            <div class="species-header-right">
                                <span class="species-stats">
                                    ${speciesData.duplicate_groups.length} groups ·
                                    ${speciesData.total_duplicates} duplicates
                                </span>
                                <button class="confirm-btn ${allConfirmed ? 'confirmed' : ''}"
                                        onclick="event.stopPropagation(); confirmSpecies('${speciesKey}')">
                                    ${allConfirmed ? '✓ Confirmed' : 'Confirm Species'}
                                </button>
                            </div>
                        </div>
                        <div class="species-groups" id="species-groups-${speciesKey}">
                `;
                speciesData.duplicate_groups.forEach(group => {
                    html += renderDuplicateGroup(speciesData.species_name, group);
                });
                html += '</div></div>';
            });
            content.innerHTML = html;
        }

        function renderDuplicateGroup(speciesName, group) {
            const groupKey = `${speciesName}:${group.group_id}`;
            const isConfirmed = confirmedGroups.has(groupKey);
            return `
                <div class="duplicate-group ${isConfirmed ? 'confirmed' : ''}" id="group-${groupKey.replace(':', '-')}">
                    <div class="group-header" onclick="toggleGroupCollapse('${speciesName}', ${group.group_id})">
                        <div class="group-header-left">
                            <span class="group-collapse-indicator">▼</span>
                            <span class="group-title">${isConfirmed ? '<span class="checkmark">✓</span>' : ''}Group ${group.group_id}</span>
                            <span class="group-count">${group.total_in_group} images</span>
                        </div>
                        <button class="confirm-btn ${isConfirmed ? 'confirmed' : ''}"
                                onclick="event.stopPropagation(); confirmGroup('${speciesName}', ${group.group_id})">
                            ${isConfirmed ? '✓ Confirmed' : 'Confirm'}
                        </button>
                    </div>
                    <div class="images-container">
                        <div class="image-card keep">
                            <div class="image-wrapper" onclick="showModal('${group.keep.path}')">
                                <img src="${group.keep.path}" alt="${group.keep.filename}" loading="lazy">
                            </div>
                            <div class="image-info">
                                <div class="image-filename">${group.keep.filename}</div>
                                <div class="image-size">${formatSize(group.keep.size)}</div>
                                <span class="image-status status-keep">Keep</span>
                            </div>
                        </div>
                        ${group.duplicates.map(dup => `
                            <div class="image-card duplicate">
                                <div class="image-wrapper" onclick="showModal('${dup.path}')">
                                    <img src="${dup.path}" alt="${dup.filename}" loading="lazy">
                                </div>
                                <div class="image-info">
                                    <div class="image-filename">${dup.filename}</div>
                                    <div class="image-size">${formatSize(dup.size)}</div>
                                    <span class="image-status status-delete">Delete</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function confirmGroup(speciesName, groupId) {
            const groupKey = `${speciesName}:${groupId}`;
            if (confirmedGroups.has(groupKey)) {
                confirmedGroups.delete(groupKey);
            } else {
                confirmedGroups.add(groupKey);
            }
            updateGroupUI(speciesName, groupId);
            updateSpeciesUI(speciesName);
            updateConfirmedCount();
        }

        function confirmSpecies(speciesName) {
            if (!currentData) return;
            const speciesData = currentData.species_results.find(s => s.species_name === speciesName);
            if (!speciesData) return;

            const allConfirmed = speciesData.duplicate_groups.every(g =>
                confirmedGroups.has(`${speciesName}:${g.group_id}`)
            );

            speciesData.duplicate_groups.forEach(group => {
                const groupKey = `${speciesName}:${group.group_id}`;
                if (allConfirmed) {
                    confirmedGroups.delete(groupKey);
                } else {
                    confirmedGroups.add(groupKey);
                }
                updateGroupUI(speciesName, group.group_id);
            });
            updateSpeciesUI(speciesName);
            updateConfirmedCount();
        }

        function toggleSpeciesCollapse(speciesName) {
            const section = document.getElementById(`species-${speciesName}`);
            if (section) {
                section.classList.toggle('collapsed');
            }
        }

        function collapseAllSpecies() {
            document.querySelectorAll('.species-section').forEach(section => {
                section.classList.add('collapsed');
            });
        }

        function expandAllSpecies() {
            document.querySelectorAll('.species-section').forEach(section => {
                section.classList.remove('collapsed');
            });
        }

        function toggleGroupCollapse(speciesName, groupId) {
            const groupKey = `${speciesName}:${groupId}`;
            const groupEl = document.getElementById(`group-${groupKey.replace(':', '-')}`);
            if (groupEl) {
                groupEl.classList.toggle('collapsed');
            }
        }

        function toggleCnnGroupCollapse(groupId) {
            const groupEl = document.getElementById(`group-${groupId}`);
            if (groupEl) {
                groupEl.classList.toggle('collapsed');
            }
        }

        function collapseAllGroups() {
            document.querySelectorAll('.duplicate-group, .similar-group').forEach(group => {
                group.classList.add('collapsed');
            });
        }

        function expandAllGroups() {
            document.querySelectorAll('.duplicate-group, .similar-group').forEach(group => {
                group.classList.remove('collapsed');
            });
        }

        function confirmAll() {
            if (!currentData) return;
            let totalGroups = 0;
            let totalFiles = 0;
            currentData.species_results.forEach(species => {
                species.duplicate_groups.forEach(group => {
                    totalGroups++;
                    totalFiles += group.duplicates.length;
                });
            });
            document.getElementById('confirmAllCount').textContent = totalGroups;
            document.getElementById('confirmAllFiles').textContent = totalFiles;
            document.getElementById('confirmAllModal').classList.add('active');
        }

        function hideConfirmAllModal() {
            document.getElementById('confirmAllModal').classList.remove('active');
        }

        function doConfirmAll() {
            if (!currentData) return;
            currentData.species_results.forEach(species => {
                species.duplicate_groups.forEach(group => {
                    confirmedGroups.add(`${species.species_name}:${group.group_id}`);
                    updateGroupUI(species.species_name, group.group_id);
                });
                updateSpeciesUI(species.species_name);
            });
            updateConfirmedCount();
            hideConfirmAllModal();
        }

        function resetConfirmations() {
            confirmedGroups.clear();
            if (currentData) {
                currentData.species_results.forEach(species => {
                    species.duplicate_groups.forEach(group => {
                        updateGroupUI(species.species_name, group.group_id);
                    });
                    updateSpeciesUI(species.species_name);
                });
            }
            updateConfirmedCount();
        }

        function updateGroupUI(speciesName, groupId) {
            const groupKey = `${speciesName}:${groupId}`;
            const isConfirmed = confirmedGroups.has(groupKey);
            const groupEl = document.getElementById(`group-${groupKey.replace(':', '-')}`);
            if (groupEl) {
                groupEl.classList.toggle('confirmed', isConfirmed);
                const btn = groupEl.querySelector('.confirm-btn');
                if (btn) {
                    btn.classList.toggle('confirmed', isConfirmed);
                    btn.innerHTML = isConfirmed ? '✓ Confirmed' : 'Confirm';
                }
                const title = groupEl.querySelector('.group-title');
                if (title) {
                    title.innerHTML = isConfirmed ? `<span class="checkmark">✓</span>Group ${groupId}` : `Group ${groupId}`;
                }
            }
        }

        function updateSpeciesUI(speciesName) {
            if (!currentData) return;
            const speciesData = currentData.species_results.find(s => s.species_name === speciesName);
            if (!speciesData) return;

            const allConfirmed = speciesData.duplicate_groups.every(g =>
                confirmedGroups.has(`${speciesName}:${g.group_id}`)
            );
            const headerEl = document.getElementById(`species-header-${speciesName}`);
            if (headerEl) {
                headerEl.classList.toggle('confirmed', allConfirmed);
                const btn = headerEl.querySelector('.confirm-btn');
                if (btn) {
                    btn.classList.toggle('confirmed', allConfirmed);
                    btn.innerHTML = allConfirmed ? '✓ Confirmed' : 'Confirm Species';
                }
                const leftSpan = headerEl.querySelector('.species-header-left span');
                if (leftSpan) {
                    leftSpan.innerHTML = `<span class="collapse-indicator">▼</span>${allConfirmed ? '<span class="checkmark">✓</span>' : ''}🌿 ${speciesName.replace(/_/g, ' ')}`;
                }
            }
        }

        function updateConfirmedCount() {
            const count = confirmedGroups.size;
            document.getElementById('confirmedCount').textContent = `${count} group${count !== 1 ? 's' : ''} confirmed`;
            document.getElementById('deleteBtn').disabled = count === 0;
        }

        function getConfirmedFilePaths() {
            // Return array of selected image paths
            return Array.from(selectedImages);
        }

        function showDeleteModal() {
            const paths = getConfirmedFilePaths();
            document.getElementById('deleteFileCount').textContent = paths.length;
            document.getElementById('deleteModal').classList.add('active');
        }

        function hideDeleteModal() {
            document.getElementById('deleteModal').classList.remove('active');
        }

        async function executeDelete() {
            const paths = getConfirmedFilePaths();
            if (paths.length === 0) {
                hideDeleteModal();
                return;
            }

            hideDeleteModal();
            document.getElementById('content').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Deleting ${paths.length} files...</p>
                </div>
            `;

            try {
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: paths })
                });
                const result = await response.json();

                if (result.success) {
                    document.getElementById('content').innerHTML = `
                        <div class="success-message">
                            ✓ Successfully deleted ${result.deleted_count} files
                        </div>
                        <p style="text-align: center; margin-top: 20px;">
                            Click "Analyze" to refresh the results.
                        </p>
                    `;
                } else {
                    document.getElementById('content').innerHTML = `
                        <div class="success-message">
                            ✓ Deleted ${result.deleted_count} files
                        </div>
                        <div class="error">
                            ${result.error_count} files could not be deleted.
                        </div>
                    `;
                }
                confirmedGroups.clear();
                selectedImages.clear();
                updateConfirmedCount();
                updateDeleteButtonState();
                document.getElementById('actionBar').style.display = 'none';
                document.getElementById('stats').style.display = 'none';
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            }
        }

        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }

        function showModal(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('active');
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal();
                hideConfirmAllModal();
                hideDeleteModal();
            }
        });

        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') analyzeDuplicates();
            });
        });
    </script>
</body>
</html>
"""


class DuplicateReviewHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the duplicate review server."""

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_html(self, content: str, status: int = 200):
        """Send HTML response."""
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_image(self, filepath: Path):
        """Send image file."""
        if not filepath.exists():
            self.send_error(404, "Image not found")
            return

        mime_type, _ = mimetypes.guess_type(str(filepath))
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "max-age=3600")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading image: {e}")

    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_html(generate_html_page())
            return

        if path == "/api/species":
            species = get_species_list()
            self.send_json(species)
            return

        # API: CNN availability check
        if path == "/api/cnn/status":
            self.send_json({"available": CNN_AVAILABLE, "model": DEFAULT_MODEL})
            return

        # API: FAISS status check
        if path == "/api/faiss/status":
            self.send_json(
                {
                    "available": FAISS_AVAILABLE,
                    "count": FAISS_STORE.index.ntotal if FAISS_STORE else 0,
                    "location": str(EMBEDDINGS_DIR) if FAISS_AVAILABLE else None,
                }
            )
            return

        # API: Get CNN similarity for species
        if path.startswith("/api/similarity/"):
            species_name = urllib.parse.unquote(path[16:])
            threshold = float(
                query.get("threshold", [str(DEFAULT_SIMILARITY_THRESHOLD)])[0]
            )
            model = query.get("model", [DEFAULT_MODEL])[0]

            if not CNN_AVAILABLE:
                self.send_json(
                    {
                        "error": "CNN not available. Install: pip install torch torchvision"
                    }
                )
                return

            result = get_species_cnn_similarity(species_name, threshold, model)
            self.send_json(result)
            return

        if path == "/api/duplicates/all":
            hash_size = int(query.get("hash_size", [str(DEFAULT_HASH_SIZE)])[0])
            threshold = int(query.get("threshold", [str(DEFAULT_HAMMING_THRESHOLD)])[0])
            result = get_all_species_duplicates(hash_size, threshold)
            self.send_json(result)
            return

        if path.startswith("/api/duplicates/"):
            species_name = urllib.parse.unquote(path[16:])
            hash_size = int(query.get("hash_size", [str(DEFAULT_HASH_SIZE)])[0])
            threshold = int(query.get("threshold", [str(DEFAULT_HAMMING_THRESHOLD)])[0])
            result = get_species_duplicates(species_name, hash_size, threshold)
            self.send_json(result)
            return

        if path.startswith("/image/"):
            parts = path[7:].split("/", 1)
            if len(parts) == 2 and BASE_DIR:
                species_name = urllib.parse.unquote(parts[0])
                filename = urllib.parse.unquote(parts[1])
                image_path = (BASE_DIR / species_name / filename).resolve()
                if image_path.is_relative_to(BASE_DIR.resolve()):
                    self.send_image(image_path)
                    return
            self.send_error(404, "Image not found")
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                files = data.get("files", [])
                result = delete_files(files)
                self.send_json(result)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)
            return

        self.send_error(404, "Not found")


def run_server(base_dir: Path, port: int = 8000):
    """Start the review server."""
    global BASE_DIR
    BASE_DIR = base_dir

    with socketserver.TCPServer(("", port), DuplicateReviewHandler) as httpd:
        print(f"\n{'=' * 60}")
        print(f"🌿 Duplicate Image Review Server")
        print(f"{'=' * 60}")
        print(f"Base directory: {base_dir}")
        print(f"Server running at: http://localhost:{port}")
        print(f"{'=' * 60}")
        print(f"\nPress Ctrl+C to stop the server.\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web-based duplicate image review tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/by_species
  %(prog)s /path/to/by_species --port 8080

Then open http://localhost:8000 in your browser.
        """,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Base directory containing species subdirectories",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )

    args = parser.parse_args()

    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    run_server(args.directory, args.port)


if __name__ == "__main__":
    main()
