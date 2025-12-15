#!/usr/bin/env python3
"""
CNN Embedding Outlier Detection

Analyzes pre-computed embeddings to detect:
- Low-quality images (outliers within species)
- Cross-species contamination (mislabeled images)
- Species with high internal variation
- Overall dataset quality issues

Requires pre-computed embeddings from batch_generate_embeddings.py

Usage:
    python detect_outliers.py
    python detect_outliers.py --visualize
    python detect_outliers.py --export-csv results.csv
"""

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
except ImportError:
    print("Error: Required dependencies not installed.")
    print("Install with: pip install numpy pandas scikit-learn")
    sys.exit(1)


def load_embeddings(embeddings_dir: Path) -> Tuple[List[Dict], Dict]:
    """Load embeddings and species stats."""
    with open(embeddings_dir / "metadata_full.pkl", "rb") as f:
        metadata = pickle.load(f)

    with open(embeddings_dir / "species_stats.json", "r") as f:
        species_stats = json.load(f)

    return metadata, species_stats


def detect_isolation_forest_outliers(
    metadata: List[Dict], contamination: float = 0.05
) -> pd.DataFrame:
    """Detect outliers using Isolation Forest."""
    embeddings_list = [m["embedding"] for m in metadata]
    embeddings_array = np.array(embeddings_list)

    # Train Isolation Forest
    iso_forest = IsolationForest(
        contamination=contamination, random_state=42, n_jobs=-1
    )

    predictions = iso_forest.fit_predict(embeddings_array)
    scores = iso_forest.score_samples(embeddings_array)

    # Build results
    results = []
    for i, m in enumerate(metadata):
        results.append(
            {
                "path": m["path"],
                "species": m["species"],
                "filename": m["filename"],
                "is_outlier": predictions[i] == -1,
                "anomaly_score": scores[i],
            }
        )

    df = pd.DataFrame(results)
    return df.sort_values("anomaly_score")


def detect_species_centroid_outliers(
    metadata: List[Dict], species_stats: Dict, threshold_percentile: float = 95
) -> Dict:
    """Detect outliers based on distance from species centroid."""
    species_embeddings = defaultdict(list)
    species_metadata = defaultdict(list)

    for m in metadata:
        species = m["species"]
        species_embeddings[species].append(m["embedding"])
        species_metadata[species].append(m)

    results = {}

    for species, embeddings_list in species_embeddings.items():
        embeddings_array = np.array(embeddings_list)
        centroid = np.array(species_stats[species]["centroid"])

        # Compute distances
        distances = []
        for emb in embeddings_list:
            emb_norm = emb / np.linalg.norm(emb)
            dist = 1 - np.dot(emb_norm, centroid)  # Cosine distance
            distances.append(dist)

        distances = np.array(distances)
        threshold = np.percentile(distances, threshold_percentile)

        # Find outliers
        outlier_indices = np.where(distances > threshold)[0]

        outliers = []
        for idx in outlier_indices:
            m = species_metadata[species][idx]
            outliers.append(
                {
                    "path": m["path"],
                    "filename": m["filename"],
                    "distance_to_centroid": distances[idx],
                    "mean_distance": species_stats[species]["mean_distance"],
                    "std_distance": species_stats[species]["std_distance"],
                }
            )

        results[species] = {
            "total_images": len(embeddings_list),
            "outliers": outliers,
            "outlier_count": len(outliers),
            "mean_distance": species_stats[species]["mean_distance"],
            "std_distance": species_stats[species]["std_distance"],
        }

    return results


def detect_cross_species_contamination(
    metadata: List[Dict], species_stats: Dict, similarity_threshold: float = 0.7
) -> List[Dict]:
    """Find images more similar to other species."""
    contamination_cases = []

    # Build centroid matrix
    species_names = sorted(species_stats.keys())
    centroids = np.array([species_stats[s]["centroid"] for s in species_names])

    for m in metadata:
        true_species = m["species"]
        emb = np.array(m["embedding"])
        emb_norm = emb / np.linalg.norm(emb)

        # Compute similarities to all centroids
        similarities = np.dot(centroids, emb_norm)

        # Find most similar species
        max_idx = np.argmax(similarities)
        most_similar_species = species_names[max_idx]
        max_similarity = similarities[max_idx]

        # Get own species similarity
        own_idx = species_names.index(true_species)
        own_similarity = similarities[own_idx]

        # Flag if more similar to different species
        if (
            most_similar_species != true_species
            and max_similarity > similarity_threshold
        ):
            contamination_cases.append(
                {
                    "path": m["path"],
                    "filename": m["filename"],
                    "labeled_as": true_species,
                    "most_similar_to": most_similar_species,
                    "own_species_similarity": float(own_similarity),
                    "other_species_similarity": float(max_similarity),
                    "similarity_gap": float(max_similarity - own_similarity),
                }
            )

    return sorted(contamination_cases, key=lambda x: x["similarity_gap"], reverse=True)


def visualize_embeddings_umap(metadata: List[Dict], save_path: Path = None):
    """Visualize embeddings using UMAP."""
    try:
        import matplotlib.pyplot as plt
        import umap
    except ImportError:
        print("UMAP visualization requires: pip install umap-learn matplotlib")
        return

    # Prepare data
    embeddings = np.array([m["embedding"] for m in metadata])
    species = [m["species"] for m in metadata]

    print("  Running UMAP dimensionality reduction...")

    # UMAP reduction
    reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        n_components=2,
        metric="cosine",
        set_op_mix_ratio=0.25,
        random_state=42,
    )

    embedding_2d = reducer.fit_transform(embeddings)

    # Plot
    fig, ax = plt.subplots(figsize=(14, 10))

    unique_species = sorted(set(species))
    colors = plt.cm.tab20(np.linspace(0, 1, min(len(unique_species), 20)))

    for i, sp in enumerate(unique_species[:20]):  # Limit to 20 for readability
        mask = np.array(species) == sp
        ax.scatter(
            embedding_2d[mask, 0],
            embedding_2d[mask, 1],
            c=[colors[i]],
            label=sp.replace("_", " "),
            alpha=0.6,
            s=30,
        )

    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    ax.set_title("UMAP Projection of Plant Species Embeddings", fontsize=14)
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"  ✓ Saved visualization to {save_path}")
    else:
        plt.show()


def generate_quality_report(
    metadata: List[Dict],
    species_stats: Dict,
    iso_df: pd.DataFrame,
    centroid_outliers: Dict,
    contamination: List[Dict],
) -> pd.DataFrame:
    """Generate comprehensive quality report."""
    quality_data = []

    for m in metadata:
        filename = m["filename"]
        species = m["species"]

        # Isolation Forest score
        iso_row = iso_df[iso_df["filename"] == filename].iloc[0]
        is_iso_outlier = iso_row["is_outlier"]
        iso_score = iso_row["anomaly_score"]

        # Centroid distance
        is_centroid_outlier = any(
            o["filename"] == filename for o in centroid_outliers[species]["outliers"]
        )

        # Cross-species contamination
        is_contamination = any(c["filename"] == filename for c in contamination)

        # Combined quality score (0-1, higher = better)
        flags = sum([is_iso_outlier, is_centroid_outlier, is_contamination])
        quality_score = 1.0 - (flags / 3.0)

        recommendation = "OK"
        if flags >= 2:
            recommendation = "REVIEW"
        elif flags == 1:
            recommendation = "CHECK"

        quality_data.append(
            {
                "path": m["path"],
                "species": species,
                "filename": filename,
                "quality_score": quality_score,
                "isolation_outlier": is_iso_outlier,
                "centroid_outlier": is_centroid_outlier,
                "cross_species": is_contamination,
                "recommendation": recommendation,
            }
        )

    df = pd.DataFrame(quality_data)
    return df.sort_values("quality_score")


def main():
    parser = argparse.ArgumentParser(
        description="Detect outliers in pre-computed CNN embeddings."
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default=Path("data/databases/embeddings"),
        help="Directory containing embeddings database",
    )

    parser.add_argument(
        "--visualize", action="store_true", help="Generate UMAP visualization"
    )

    parser.add_argument("--export-csv", type=Path, help="Export quality report to CSV")

    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Expected contamination rate for Isolation Forest",
    )

    args = parser.parse_args()

    # Check if embeddings exist
    if not args.embeddings_dir.exists():
        print(f"Error: Embeddings directory not found: {args.embeddings_dir}")
        print("Run batch_generate_embeddings.py first to generate embeddings.")
        return 1

    # Load embeddings
    print("Loading embeddings...")
    try:
        metadata, species_stats = load_embeddings(args.embeddings_dir)
    except FileNotFoundError as e:
        print(f"Error: Required file not found: {e}")
        print("Run batch_generate_embeddings.py first to generate embeddings.")
        return 1

    print(f"  Loaded {len(metadata)} embeddings")
    print(f"  Species: {len(species_stats)}")
    print()

    # Run outlier detection
    print("Running Isolation Forest...")
    iso_df = detect_isolation_forest_outliers(metadata, args.contamination)
    iso_outliers = iso_df[iso_df["is_outlier"]]
    print(f"  Detected {len(iso_outliers)} outliers")
    print()

    print("Detecting species centroid outliers...")
    centroid_outliers = detect_species_centroid_outliers(metadata, species_stats)
    total_centroid = sum(r["outlier_count"] for r in centroid_outliers.values())
    print(f"  Detected {total_centroid} outliers")
    print()

    print("Detecting cross-species contamination...")
    contamination = detect_cross_species_contamination(metadata, species_stats)
    print(f"  Detected {len(contamination)} potential contamination cases")
    print()

    # Generate quality report
    print("Generating quality report...")
    quality_df = generate_quality_report(
        metadata, species_stats, iso_df, centroid_outliers, contamination
    )

    review_count = (quality_df["recommendation"] == "REVIEW").sum()
    check_count = (quality_df["recommendation"] == "CHECK").sum()
    ok_count = (quality_df["recommendation"] == "OK").sum()

    print(f"  REVIEW: {review_count}")
    print(f"  CHECK: {check_count}")
    print(f"  OK: {ok_count}")
    print()

    # Export
    if args.export_csv:
        quality_df.to_csv(args.export_csv, index=False)
        print(f"✓ Exported quality report to {args.export_csv}")
        print()

    # Visualize
    if args.visualize:
        print("Generating UMAP visualization...")
        viz_path = args.embeddings_dir / "umap_visualization.png"
        visualize_embeddings_umap(metadata, viz_path)
        print()

    # Print summary
    print("=" * 60)
    print("OUTLIER DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total images analyzed: {len(metadata)}")
    print(f"Species analyzed: {len(species_stats)}")
    print()
    print(f"Isolation Forest outliers: {len(iso_outliers)}")
    print(f"Centroid outliers: {total_centroid}")
    print(f"Cross-species contamination: {len(contamination)}")
    print()
    print("Quality Recommendations:")
    print(f"  REVIEW (2-3 flags): {review_count}")
    print(f"  CHECK (1 flag): {check_count}")
    print(f"  OK (0 flags): {ok_count}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
