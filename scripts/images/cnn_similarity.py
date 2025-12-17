#!/usr/bin/env python3
"""
CNN-based Image Similarity Module

Uses a pre-trained ResNet model to extract deep features from images
and find semantically similar images within a species directory.

This complements perceptual hash duplicate detection by finding images
that are visually similar (same plant, different angles) rather than
pixel-level duplicates.

Dependencies:
    pip install torch torchvision Pillow

Usage:
    # As standalone script
    python cnn_similarity.py /path/to/species/directory

    # As module
    from cnn_similarity import compute_cnn_embeddings, find_similar_groups
    embeddings = compute_cnn_embeddings(image_paths)
    groups = find_similar_groups(embeddings, threshold=0.85)
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from utils import UnionFind, get_image_files

# Default similarity threshold (cosine similarity, 0-1)
# Higher = more strict (only very similar images)
DEFAULT_SIMILARITY_THRESHOLD = 0.85

# Model to use for feature extraction
DEFAULT_MODEL = "resnet18"  # Options: resnet18, resnet50, resnet101


@dataclass
class SimilarityResult:
    """Result of similarity analysis for a species directory."""

    species_name: str
    directory: Path
    total_images: int
    processed_images: int
    similar_groups: int
    images_in_groups: int
    similarity_threshold: float
    model_name: str
    group_details: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "species_name": self.species_name,
            "directory": str(self.directory),
            "total_images": self.total_images,
            "processed_images": self.processed_images,
            "similar_groups": self.similar_groups,
            "images_in_groups": self.images_in_groups,
            "similarity_threshold": self.similarity_threshold,
            "model_name": self.model_name,
            "group_details": self.group_details,
            "errors": self.errors,
        }


def load_model(model_name: str = DEFAULT_MODEL):
    """
    Load a pre-trained CNN model for feature extraction.

    Args:
        model_name: Name of the model (resnet18, resnet50, resnet101)

    Returns:
        Tuple of (model, transform, device)
    """
    try:
        import torch
        import torchvision.models as models
        import torchvision.transforms as transforms
    except ImportError:
        raise ImportError(
            "PyTorch and torchvision are required for CNN similarity. "
            "Install with: pip install torch torchvision"
        )

    # Select device (prioritize Apple Silicon MPS, then CUDA, then CPU)
    # Note: MPS can be unstable on Python 3.13, use CPU as fallback if issues occur
    import os
    import sys

    # Check if CPU mode is forced via environment variable
    force_cpu = os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"

    use_mps = torch.backends.mps.is_available() and not force_cpu

    # Check for MPS issues (Python 3.13 compatibility)
    if use_mps and sys.version_info >= (3, 13):
        print("Warning: Python 3.13 detected. MPS may be unstable.")
        print("If you experience crashes, run with --cpu flag")

    if use_mps:
        try:
            device = torch.device("mps")
            # Test MPS with a small tensor to catch issues early
            test_tensor = torch.zeros(1, device=device)
            del test_tensor  # Clean up
            print("Using Apple Silicon MPS backend")
        except Exception as e:
            print(f"MPS initialization failed: {e}")
            print("Falling back to CPU")
            device = torch.device("cpu")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("Using CUDA GPU")
    else:
        device = torch.device("cpu")
        print("Using CPU")

    # Load pre-trained model
    if model_name == "resnet18":
        model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    elif model_name == "resnet50":
        model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
    elif model_name == "resnet101":
        model = models.resnet101(weights=models.ResNet101_Weights.IMAGENET1K_V1)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Remove the final classification layer to get features
    model = torch.nn.Sequential(*list(model.children())[:-1])
    model = model.to(device)
    model.eval()

    # Standard ImageNet preprocessing
    transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    return model, transform, device


def extract_embedding(
    image_path: Path, model, transform, device
) -> Optional[List[float]]:
    """
    Extract CNN embedding for a single image.

    Args:
        image_path: Path to the image
        model: Pre-trained CNN model
        transform: Image preprocessing transform
        device: torch device

    Returns:
        List of floats representing the embedding, or None on error
    """
    try:
        import torch
        from PIL import Image
    except ImportError:
        return None

    try:
        # Load and preprocess image
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        img_tensor = transform(img).unsqueeze(0).to(device)

        # Extract features
        with torch.no_grad():
            features = model(img_tensor)
            # Flatten and normalize
            features = features.squeeze()
            features = features / features.norm()

        return features.cpu().tolist()

    except Exception as e:
        return None


def compute_cnn_embeddings(
    image_paths: List[Path], model_name: str = DEFAULT_MODEL, verbose: bool = True
) -> Tuple[Dict[Path, List[float]], List[Tuple[str, str]]]:
    """
    Compute CNN embeddings for a list of images.

    Args:
        image_paths: List of image file paths
        model_name: Name of the model to use
        verbose: Print progress information

    Returns:
        Tuple of (embedding_map, errors)
        - embedding_map: Dict mapping paths to embedding vectors
        - errors: List of (filename, error_message) tuples
    """
    if verbose:
        print(f"Loading {model_name} model...")

    model, transform, device = load_model(model_name)

    embeddings: Dict[Path, List[float]] = {}
    errors: List[Tuple[str, str]] = []

    total = len(image_paths)
    for i, img_path in enumerate(image_paths, 1):
        if verbose and i % 10 == 0:
            print(f"  Processing {i}/{total}...")

        embedding = extract_embedding(img_path, model, transform, device)
        if embedding is not None:
            embeddings[img_path] = embedding
        else:
            errors.append((img_path.name, "Failed to extract embedding"))

    if verbose:
        print(f"  Extracted embeddings for {len(embeddings)}/{total} images")

    return embeddings, errors


def compute_cnn_embeddings_batch(
    image_paths: List[Path],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
    verbose: bool = True,
) -> Tuple[Dict[Path, List[float]], List[Tuple[str, str]]]:
    """
    Compute CNN embeddings in batches for improved efficiency.

    This function is optimized for GPU/MPS processing by batching multiple
    images together, which significantly improves throughput.

    Args:
        image_paths: List of image file paths
        model_name: Name of the model to use
        batch_size: Number of images to process at once
        verbose: Print progress information

    Returns:
        Tuple of (embedding_map, errors)
        - embedding_map: Dict mapping paths to embedding vectors
        - errors: List of (filename, error_message) tuples
    """
    try:
        import torch
        from PIL import Image
    except ImportError:
        # Fallback to non-batch version
        print("Falling back to non-batch version due to import error")
        return compute_cnn_embeddings(image_paths, model_name, verbose)

    if verbose:
        print(f"Loading {model_name} model for batch processing...")

    model, transform, device = load_model(model_name)

    embeddings: Dict[Path, List[float]] = {}
    errors: List[Tuple[str, str]] = []

    # Process in batches
    total = len(image_paths)
    num_batches = (total + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total)
        batch_paths = image_paths[start_idx:end_idx]

        if verbose and batch_idx % 10 == 0:
            print(f"  Batch {batch_idx + 1}/{num_batches} ({end_idx}/{total} images)")

        # Load and preprocess batch
        batch_tensors = []
        valid_paths = []

        for img_path in batch_paths:
            try:
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img_tensor = transform(img)
                batch_tensors.append(img_tensor)
                valid_paths.append(img_path)
            except Exception as e:
                errors.append((img_path.name, str(e)))

        if not batch_tensors:
            continue

        # Stack into batch and move to device
        try:
            batch_tensor = torch.stack(batch_tensors).to(device)

            # Extract features
            with torch.no_grad():
                features = model(batch_tensor)
                # Flatten and normalize each embedding
                features = features.squeeze()
                if len(features.shape) == 1:  # Single image batch
                    features = features.unsqueeze(0)
                features = features / features.norm(dim=1, keepdim=True)

            # Convert to lists and store
            features_cpu = features.cpu()
            for i, img_path in enumerate(valid_paths):
                embeddings[img_path] = features_cpu[i].tolist()

        except Exception as e:
            # If batch processing fails, process individually
            for img_path in valid_paths:
                embedding = extract_embedding(img_path, model, transform, device)
                if embedding is not None:
                    embeddings[img_path] = embedding
                else:
                    errors.append((img_path.name, f"Batch processing failed: {str(e)}"))

    if verbose:
        print(f"  Extracted embeddings for {len(embeddings)}/{total} images")

    return embeddings, errors


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity (0-1, higher = more similar)
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def find_similar_groups(
    embeddings: Dict[Path, List[float]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    exclude_pairs: Optional[Set[Tuple[str, str]]] = None,
) -> List[Set[Path]]:
    """
    Find groups of similar images based on embedding similarity.

    Uses Union-Find algorithm for efficient grouping.

    Args:
        embeddings: Dict mapping image paths to embedding vectors
        threshold: Minimum cosine similarity to consider similar
        exclude_pairs: Set of (filename1, filename2) pairs to exclude
                      (e.g., already identified as duplicates)

    Returns:
        List of sets, where each set contains paths of similar images
    """
    paths = list(embeddings.keys())
    n = len(paths)

    if n < 2:
        return []

    if exclude_pairs is None:
        exclude_pairs = set()

    uf = UnionFind(n)

    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            name_i, name_j = paths[i].name, paths[j].name

            # Skip if this pair is in exclusion list
            if (name_i, name_j) in exclude_pairs or (name_j, name_i) in exclude_pairs:
                continue

            similarity = cosine_similarity(embeddings[paths[i]], embeddings[paths[j]])
            if similarity >= threshold:
                uf.union(i, j)

    # Convert index groups to path groups
    return [{paths[i] for i in members} for members in uf.groups_with_multiple()]


def analyze_species_similarity(
    species_directory: Path,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    model_name: str = DEFAULT_MODEL,
    exclude_duplicates: Optional[Set[Tuple[str, str]]] = None,
    verbose: bool = True,
) -> SimilarityResult:
    """
    Analyze a species directory for similar images using CNN features.

    Args:
        species_directory: Path to the species image directory
        similarity_threshold: Minimum cosine similarity (0-1)
        model_name: CNN model to use
        exclude_duplicates: Pairs of filenames to exclude (already duplicates)
        verbose: Print progress

    Returns:
        SimilarityResult with details of similar image groups
    """
    species_directory = Path(species_directory)
    species_name = species_directory.name

    result = SimilarityResult(
        species_name=species_name,
        directory=species_directory,
        total_images=0,
        processed_images=0,
        similar_groups=0,
        images_in_groups=0,
        similarity_threshold=similarity_threshold,
        model_name=model_name,
    )

    if not species_directory.exists() or not species_directory.is_dir():
        result.errors.append(("directory", f"Invalid directory: {species_directory}"))
        return result

    # Get image files
    image_files = get_image_files(species_directory)
    result.total_images = len(image_files)

    if result.total_images < 2:
        if verbose:
            print(f"[{species_name}] Not enough images for similarity analysis")
        return result

    if verbose:
        print(
            f"[{species_name}] Analyzing {result.total_images} images for similarity..."
        )

    # Compute embeddings
    embeddings, errors = compute_cnn_embeddings(image_files, model_name, verbose)
    result.processed_images = len(embeddings)
    result.errors.extend(errors)

    # Find similar groups
    similar_groups = find_similar_groups(
        embeddings, similarity_threshold, exclude_duplicates
    )
    result.similar_groups = len(similar_groups)

    # Format group details
    for i, group in enumerate(similar_groups, 1):
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

        result.group_details.append(
            {
                "group_id": i,
                "images": group_images,
                "count": len(group_images),
            }
        )
        result.images_in_groups += len(group_images)

    if verbose:
        print(
            f"[{species_name}] Found {result.similar_groups} groups of similar images"
        )

    return result


def embeddings_to_json(
    embeddings: Dict[Path, List[float]], species_name: str
) -> List[Dict]:
    """
    Convert embeddings to JSON-serializable format.

    Args:
        embeddings: Dict mapping paths to embedding vectors
        species_name: Name of the species

    Returns:
        List of dicts with filename, path, and embedding
    """
    result = []
    for path, embedding in embeddings.items():
        result.append(
            {
                "filename": path.name,
                "size": path.stat().st_size,
                "path": f"/image/{species_name}/{path.name}",
                "embedding": embedding,
            }
        )
    return result


def json_to_embeddings(data: List[Dict], base_dir: Path) -> Dict[Path, List[float]]:
    """
    Convert JSON data back to embeddings dict.

    Args:
        data: List of dicts from embeddings_to_json
        base_dir: Base directory for image paths

    Returns:
        Dict mapping paths to embedding vectors
    """
    embeddings = {}
    for item in data:
        # Reconstruct path from the stored path
        path_parts = item["path"].split("/")
        if len(path_parts) >= 3:
            species_name = path_parts[2]
            filename = path_parts[3] if len(path_parts) > 3 else item["filename"]
            full_path = base_dir / species_name / filename
            if full_path.exists():
                embeddings[full_path] = item["embedding"]
    return embeddings


def main():
    """Main function for standalone script execution."""
    parser = argparse.ArgumentParser(
        description="Find similar images using CNN features.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/species/Acacia_baileyana
  %(prog)s /path/to/species/Acacia_baileyana --threshold 0.90
  %(prog)s /path/to/species/Acacia_baileyana --model resnet50
        """,
    )

    parser.add_argument(
        "directory", type=Path, help="Path to the species image directory"
    )

    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"Similarity threshold 0-1 (default: {DEFAULT_SIMILARITY_THRESHOLD})",
    )

    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=["resnet18", "resnet50", "resnet101"],
        help=f"CNN model to use (default: {DEFAULT_MODEL})",
    )

    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="Output JSON file for results"
    )

    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress output"
    )

    args = parser.parse_args()

    # Validate
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Run analysis
    result = analyze_species_similarity(
        species_directory=args.directory,
        similarity_threshold=args.threshold,
        model_name=args.model,
        verbose=not args.quiet,
    )

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"SIMILARITY ANALYSIS: {result.species_name}")
    print(f"{'=' * 60}")
    print(f"Total images:        {result.total_images}")
    print(f"Processed:           {result.processed_images}")
    print(f"Similar groups:      {result.similar_groups}")
    print(f"Images in groups:    {result.images_in_groups}")
    print(f"Threshold:           {result.similarity_threshold}")
    print(f"Model:               {result.model_name}")

    if result.errors:
        print(f"Errors:              {len(result.errors)}")

    print(f"{'=' * 60}\n")

    # Print groups
    if result.group_details:
        print("Similar Image Groups:")
        for group in result.group_details:
            print(f"\n  Group {group['group_id']} ({group['count']} images):")
            for img in group["images"]:
                print(f"    - {img['filename']} ({img['size']} bytes)")

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {args.output}")

    sys.exit(0)


if __name__ == "__main__":
    main()
