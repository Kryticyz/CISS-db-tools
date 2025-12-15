#!/usr/bin/env python3
"""
Batch CNN Embedding Generator

Pre-computes CNN embeddings for all plant species images and stores
them in a FAISS vector database for instant similarity searches.

Usage:
    python batch_generate_embeddings.py /path/to/by_species
    python batch_generate_embeddings.py /path/to/by_species --model resnet50
    python batch_generate_embeddings.py /path/to/by_species --cpu  # Force CPU mode

Note: If experiencing MPS crashes on Python 3.13, use --cpu flag
"""

import argparse
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List

# Disable PyTorch's internal multiprocessing to avoid semaphore leaks
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Allow duplicate OpenMP libraries (PyTorch, NumPy, FAISS may each have their own)
# This is needed on macOS where Homebrew packages often link different OpenMP versions
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import faiss
    import numpy as np
    from tqdm import tqdm
except ImportError:
    print("Error: Required dependencies not installed.")
    print("Install with: pip install faiss-cpu numpy tqdm")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cnn_similarity import (
    DEFAULT_MODEL,
    compute_cnn_embeddings_batch,
    get_image_files,
    load_model,
)


def process_species(species_dir: Path, model_name: str, batch_size: int) -> Dict:
    """
    Process a single species directory.

    Returns:
        Dict with embeddings, metadata, and stats
    """
    species_name = species_dir.name
    image_files = get_image_files(species_dir)

    if len(image_files) == 0:
        return {
            "species_name": species_name,
            "embeddings": {},
            "metadata": [],
            "errors": [],
            "stats": {"total": 0, "processed": 0, "errors": 0},
        }

    # Compute embeddings with batching
    embeddings, errors = compute_cnn_embeddings_batch(
        image_files,
        model_name=model_name,
        batch_size=batch_size,
        verbose=False,  # Suppress per-species output
    )

    # Build metadata
    metadata = []
    for img_path, embedding in embeddings.items():
        metadata.append(
            {
                "filename": img_path.name,
                "species": species_name,
                "path": str(img_path),
                "size": img_path.stat().st_size,
                "embedding": embedding,
            }
        )

    return {
        "species_name": species_name,
        "embeddings": embeddings,
        "metadata": metadata,
        "errors": errors,
        "stats": {
            "total": len(image_files),
            "processed": len(embeddings),
            "errors": len(errors),
        },
    }


def build_faiss_index(all_metadata: List[Dict], dimension: int = 512) -> faiss.Index:
    """Build FAISS index from metadata."""
    # Extract embeddings
    embeddings_list = [m["embedding"] for m in all_metadata]
    embeddings_array = np.array(embeddings_list, dtype="float32")

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings_array)

    # Create index (Inner Product = Cosine after normalization)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_array)

    return index


def compute_species_statistics(all_metadata: List[Dict]) -> Dict:
    """Compute per-species statistics and centroids."""
    from collections import defaultdict

    species_data = defaultdict(list)

    # Group by species
    for item in all_metadata:
        species_data[item["species"]].append(item["embedding"])

    # Compute centroids and stats
    species_stats = {}
    for species, embeddings_list in species_data.items():
        embeddings_array = np.array(embeddings_list, dtype="float32")

        # Compute centroid
        centroid = embeddings_array.mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)  # Normalize

        # Compute intra-species distances
        distances = []
        for emb in embeddings_list:
            emb_norm = emb / np.linalg.norm(emb)
            dist = 1 - np.dot(emb_norm, centroid)  # Cosine distance
            distances.append(dist)

        species_stats[species] = {
            "count": len(embeddings_list),
            "centroid": centroid.tolist(),
            "mean_distance": float(np.mean(distances)),
            "std_distance": float(np.std(distances)),
            "min_distance": float(np.min(distances)),
            "max_distance": float(np.max(distances)),
        }

    return species_stats


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate CNN embeddings for all species."
    )

    parser.add_argument(
        "base_dir", type=Path, help="Base directory containing species subdirectories"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=["resnet18", "resnet50", "resnet101"],
        help="CNN model to use",
    )

    parser.add_argument(
        "--batch-size", type=int, default=32, help="Batch size for CNN processing"
    )

    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU mode (use if MPS causes crashes on Python 3.13)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/databases/embeddings"),
        help="Output directory for embeddings database",
    )

    args = parser.parse_args()

    # Force CPU mode if requested (workaround for MPS issues)
    if args.cpu:
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        os.environ["PYTORCH_MPS_PREFER_METAL"] = "0"
        print("CPU mode forced (MPS disabled)")
        print()

    # Validate input
    if not args.base_dir.exists():
        print(f"Error: Directory not found: {args.base_dir}")
        return 1

    # Get species directories
    species_dirs = [
        d
        for d in sorted(args.base_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    ]

    print(f"Found {len(species_dirs)} species directories")
    print(f"Using model: {args.model}")
    print(f"Batch size: {args.batch_size}")
    print()
    print(
        "Note: Processing species sequentially (GPU contexts cannot be shared across processes)"
    )
    print()

    # Process species sequentially with progress bar
    # (PyTorch MPS/CUDA contexts cannot be pickled for multiprocessing)
    all_metadata = []
    total_images = 0
    total_processed = 0
    total_errors = 0

    with tqdm(total=len(species_dirs), desc="Processing species") as pbar:
        for species_dir in species_dirs:
            result = process_species(species_dir, args.model, args.batch_size)

            all_metadata.extend(result["metadata"])
            total_images += result["stats"]["total"]
            total_processed += result["stats"]["processed"]
            total_errors += result["stats"]["errors"]

            pbar.set_postfix(
                {
                    "species": result["species_name"][:20],
                    "processed": result["stats"]["processed"],
                    "errors": result["stats"]["errors"],
                }
            )
            pbar.update(1)

    print()
    print(f"Processing complete!")
    print(f"  Total images: {total_images}")
    print(f"  Processed: {total_processed}")
    print(f"  Errors: {total_errors}")
    print()

    if total_processed == 0:
        print("Error: No embeddings were generated!")
        return 1

    # Build FAISS index
    print("Building FAISS index...")
    index = build_faiss_index(all_metadata, dimension=512)
    print(f"  Index built with {index.ntotal} vectors")
    print()

    # Compute species statistics
    print("Computing species statistics...")
    species_stats = compute_species_statistics(all_metadata)
    print(f"  Stats computed for {len(species_stats)} species")
    print()

    # Save to disk
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Saving to {args.output}...")

    # Save FAISS index
    faiss.write_index(index, str(args.output / "embeddings.index"))
    print("  ✓ embeddings.index")

    # Save metadata (without embeddings to save space)
    metadata_slim = [
        {k: v for k, v in m.items() if k != "embedding"} for m in all_metadata
    ]
    with open(args.output / "metadata.pkl", "wb") as f:
        pickle.dump(metadata_slim, f)
    print("  ✓ metadata.pkl")

    # Save full metadata with embeddings (for outlier detection)
    with open(args.output / "metadata_full.pkl", "wb") as f:
        pickle.dump(all_metadata, f)
    print("  ✓ metadata_full.pkl")

    # Save species stats
    with open(args.output / "species_stats.json", "w") as f:
        json.dump(species_stats, f, indent=2)
    print("  ✓ species_stats.json")

    # Save summary
    summary = {
        "model": args.model,
        "total_species": len(species_dirs),
        "total_images": total_images,
        "total_processed": total_processed,
        "total_errors": total_errors,
        "embedding_dimension": 512,
        "index_size": index.ntotal,
        "batch_size": args.batch_size,
    }
    with open(args.output / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("  ✓ summary.json")

    print()
    print("✅ Embeddings database created successfully!")
    print(f"   Location: {args.output.absolute()}")

    return 0


if __name__ == "__main__":
    # Set multiprocessing start method to avoid semaphore leaks
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # Already set

    # Disable torch internal threading which can cause issues
    try:
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except ImportError:
        pass

    exit(main())
