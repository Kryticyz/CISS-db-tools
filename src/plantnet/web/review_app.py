"""
Web-based Duplicate Image Review Tool

A local web server that provides a visual interface for reviewing duplicate
image groups detected by the deduplication system. Useful for:
- Verifying that detected duplicates are actually similar
- Tuning threshold values for perceptual hashing
- Reviewing deduplication results before deletion

Usage:
    from plantnet.web.review_app import run_server
    run_server(Path("/path/to/by_species"))

    # Or use CLI:
    plantnet-review /path/to/by_species
    plantnet-review /path/to/by_species --port 8080

Then open http://localhost:8000 in your browser.

Dependencies:
    All dependencies are managed through conda environment.yml
"""

import argparse
import http.server
import json
import mimetypes
import socketserver
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from plantnet package
from plantnet.images.deduplication import (
    DEFAULT_HAMMING_THRESHOLD,
    DEFAULT_HASH_SIZE,
    IMAGE_EXTENSIONS,
    compute_image_hash,
    find_duplicate_groups,
    get_image_files,
    select_images_to_keep,
)
from plantnet.utils.paths import EMBEDDINGS_DIR

# Try to import CNN similarity module
CNN_AVAILABLE = False
try:
    from plantnet.images.similarity import (
        DEFAULT_MODEL,
        DEFAULT_SIMILARITY_THRESHOLD,
        compute_cnn_embeddings,
        cosine_similarity,
    )
    from plantnet.images.similarity import (
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


class FAISSEmbeddingStore:
    """FAISS-based embedding store for fast similarity search."""

    def __init__(self, embeddings_dir: Path):
        try:
            import pickle

            import faiss
        except ImportError:
            raise ImportError(
                "FAISS not available. Install with: conda install faiss-cpu"
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

    embeddings_path = EMBEDDINGS_DIR
    if embeddings_path.exists() and (embeddings_path / "embeddings.index").exists():
        try:
            FAISS_STORE = FAISSEmbeddingStore(embeddings_path)
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


def get_species_outliers(
    species_name: str,
    similarity_threshold: float = 0.75,
    centroid_std_multiplier: float = 2.0,
) -> Dict[str, Any]:
    """
    Get outlier images for a species.

    Outliers are identified as:
    1. Images with no similar matches above threshold (isolated)
    2. Images significantly different from species average (far from centroid)

    Args:
        species_name: Name of the species to analyze
        similarity_threshold: Images with max similarity below this are "isolated".
            Lower = more sensitive (more outliers). Default 0.75.
        centroid_std_multiplier: Images beyond (mean + X * std) distance from
            centroid are "distant". Lower = more sensitive. Default 2.0.

    Returns dict with outlier information.
    """
    if FAISS_STORE is None:
        return {"error": "FAISS store not available. Pre-computed embeddings required."}

    try:
        import pickle
        import numpy as np
    except ImportError:
        return {"error": "NumPy required for outlier detection"}

    try:
        # Get all images for this species
        species_items = [m for m in FAISS_STORE.metadata if m["species"] == species_name]
        if len(species_items) < 3:
            return {
                "species_name": species_name,
                "outliers": [],
                "message": "Not enough images for outlier detection (need at least 3)",
            }

        # Get their indices and embeddings
        species_indices = [
            i for i, m in enumerate(FAISS_STORE.metadata) if m["species"] == species_name
        ]

        with open(FAISS_STORE.embeddings_dir / "metadata_full.pkl", "rb") as f:
            full_metadata = pickle.load(f)

        species_embeddings = [full_metadata[i]["embedding"] for i in species_indices]
        embeddings_array = np.array(species_embeddings, dtype="float32")

        # Normalize embeddings
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / norms

        # Calculate centroid
        centroid = np.mean(embeddings_array, axis=0)
        centroid = centroid / np.linalg.norm(centroid)

        # Calculate distance from centroid for each image
        distances_from_centroid = 1 - np.dot(embeddings_array, centroid)

        # Calculate max similarity to any other image
        n = len(species_embeddings)
        max_similarities = []
        for i in range(n):
            similarities = [np.dot(embeddings_array[i], embeddings_array[j])
                          for j in range(n) if i != j]
            max_similarities.append(max(similarities) if similarities else 0)

        max_similarities = np.array(max_similarities)

        # Identify outliers
        # Type 1: Isolated (no matches above threshold)
        isolated_mask = max_similarities < similarity_threshold

        # Type 2: Far from centroid (use mean + multiplier * std as threshold)
        distance_threshold = np.mean(distances_from_centroid) + centroid_std_multiplier * np.std(distances_from_centroid)
        far_from_centroid_mask = distances_from_centroid > distance_threshold

        # Combine both types
        outlier_mask = isolated_mask | far_from_centroid_mask

        outliers = []
        for idx, is_outlier in enumerate(outlier_mask):
            if is_outlier:
                item = species_items[idx]
                outlier_type = []
                if isolated_mask[idx]:
                    outlier_type.append("isolated")
                if far_from_centroid_mask[idx]:
                    outlier_type.append("distant")

                outliers.append({
                    "filename": item["filename"],
                    "size": item["size"],
                    "path": f"/image/{species_name}/{item['filename']}",
                    "max_similarity": float(max_similarities[idx]),
                    "distance_from_centroid": float(distances_from_centroid[idx]),
                    "outlier_types": outlier_type,
                })

        return {
            "species_name": species_name,
            "total_images": len(species_items),
            "outliers": outliers,
            "outlier_count": len(outliers),
            "similarity_threshold": similarity_threshold,
            "centroid_std_multiplier": centroid_std_multiplier,
            "distance_threshold": float(distance_threshold),
        }
    except Exception as e:
        return {"error": f"Failed to detect outliers: {str(e)}"}


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


def get_species_combined(
    species_name: str,
    similarity_threshold: float = 0.85,
    hash_size: int = DEFAULT_HASH_SIZE,
    hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    outlier_isolation_threshold: float = 0.75,
    outlier_centroid_multiplier: float = 2.0,
) -> Dict[str, Any]:
    """
    Get combined view with all three detection types:
    - CNN similarity groups
    - Direct duplicates (perceptual hash)
    - Outliers

    Returns dict with all detections marked by type.
    """
    results = {
        "species_name": species_name,
        "similarity_threshold": similarity_threshold,
        "hamming_threshold": hamming_threshold,
        "hash_size": hash_size,
        "outlier_isolation_threshold": outlier_isolation_threshold,
        "outlier_centroid_multiplier": outlier_centroid_multiplier,
        "items": [],
    }

    # Get CNN similarity groups
    cnn_result = get_species_cnn_similarity(species_name, similarity_threshold)
    if "similar_groups" in cnn_result:
        for group in cnn_result["similar_groups"]:
            results["items"].append({
                "type": "cnn_similarity",
                "group_id": group["group_id"],
                "images": group["images"],
                "count": group["count"],
            })

    # Get direct duplicates
    dup_result = get_species_duplicates(species_name, hash_size, hamming_threshold)
    if "duplicate_groups" in dup_result:
        for group in dup_result["duplicate_groups"]:
            # Flatten keep and duplicates into single list
            images = [group["keep"]] + group["duplicates"]
            results["items"].append({
                "type": "duplicate",
                "group_id": group["group_id"],
                "images": images,
                "count": len(images),
                "keep": group["keep"]["filename"],
            })

    # Get outliers
    outlier_result = get_species_outliers(species_name, outlier_isolation_threshold, outlier_centroid_multiplier)
    if "outliers" in outlier_result:
        # Each outlier is its own "group"
        for idx, outlier in enumerate(outlier_result["outliers"], 1):
            results["items"].append({
                "type": "outlier",
                "group_id": idx,
                "images": [outlier],
                "count": 1,
                "outlier_types": outlier.get("outlier_types", []),
            })

    results["total_items"] = len(results["items"])
    return results


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
    """Generate the main HTML page.

    Returns the complete HTML page with embedded CSS and JavaScript.
    This is the single-page application for duplicate review.
    """
    # Read the HTML template from the original file
    # For now, we'll embed it directly (can be extracted to template later)
    original_script = (
        Path(__file__).parent.parent.parent.parent
        / "scripts"
        / "images"
        / "review_duplicates.py"
    )

    if original_script.exists():
        with open(original_script, "r") as f:
            content = f.read()
            # Extract HTML from generate_html_page function
            start = content.find('return """<!DOCTYPE html>')
            if start != -1:
                start += len('return """')
                end = content.find('"""', start)
                if end != -1:
                    return content[start:end]

    # Fallback: minimal HTML if template not found
    return """<!DOCTYPE html>
<html>
<head>
    <title>Duplicate Image Review</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Duplicate Image Review</h1>
    <p>Template file not found. Please ensure the application is properly installed.</p>
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

        # API: Get outliers for species
        if path.startswith("/api/outliers/"):
            species_name = urllib.parse.unquote(path[14:])
            threshold = float(
                query.get("threshold", ["0.75"])[0]
            )
            centroid_multiplier = float(
                query.get("centroid_multiplier", ["2.0"])[0]
            )

            result = get_species_outliers(species_name, threshold, centroid_multiplier)
            self.send_json(result)
            return

        # API: Get combined view for species
        if path.startswith("/api/combined/"):
            species_name = urllib.parse.unquote(path[14:])
            similarity_threshold = float(
                query.get("similarity_threshold", [str(DEFAULT_SIMILARITY_THRESHOLD)])[0]
            )
            hamming_threshold = int(
                query.get("hamming_threshold", [str(DEFAULT_HAMMING_THRESHOLD)])[0]
            )
            hash_size = int(query.get("hash_size", [str(DEFAULT_HASH_SIZE)])[0])
            outlier_isolation_threshold = float(
                query.get("outlier_isolation_threshold", ["0.75"])[0]
            )
            outlier_centroid_multiplier = float(
                query.get("outlier_centroid_multiplier", ["2.0"])[0]
            )

            result = get_species_combined(
                species_name, similarity_threshold, hash_size, hamming_threshold,
                outlier_isolation_threshold, outlier_centroid_multiplier
            )
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
    """
    Start the duplicate review web server.

    Args:
        base_dir: Path to directory containing species subdirectories
        port: Port number to run server on (default: 8000)
    """
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
    """Main entry point for CLI."""
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
