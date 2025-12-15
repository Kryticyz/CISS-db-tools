"""
Image processing command-line interfaces.

Provides CLI wrappers for deduplication, CNN similarity, and image downloading.
"""

import argparse
import sys
from pathlib import Path

from plantnet.images.deduplication import (
    DEFAULT_HAMMING_THRESHOLD,
    DEFAULT_HASH_SIZE,
    deduplicate_species_images,
)
from plantnet.images.similarity import (
    DEFAULT_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    analyze_species_similarity,
)


def deduplicate_cli():
    """CLI for image deduplication using perceptual hashing."""
    parser = argparse.ArgumentParser(
        prog="plantnet-deduplicate",
        description="Detect and mark duplicate images using perceptual hashing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet-deduplicate /path/to/species/Acacia_dealbata
  plantnet-deduplicate /path/to/species/Acacia_dealbata --threshold 3
  plantnet-deduplicate /path/to/species/Acacia_dealbata --exact
        """,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Path to the species image directory",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for output file (default: same as input directory)",
    )

    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=DEFAULT_HAMMING_THRESHOLD,
        help=f"Hamming distance threshold (default: {DEFAULT_HAMMING_THRESHOLD})",
    )

    parser.add_argument(
        "-s",
        "--hash-size",
        type=int,
        default=DEFAULT_HASH_SIZE,
        help=f"Hash size for perceptual hashing (default: {DEFAULT_HASH_SIZE})",
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count)",
    )

    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use MD5 file hash for exact duplicate detection only",
    )

    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress output"
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Run deduplication
    result = deduplicate_species_images(
        species_directory=args.directory,
        output_dir=args.output_dir,
        hash_size=args.hash_size,
        hamming_threshold=args.threshold,
        max_workers=args.workers,
        use_file_hash=args.exact,
        verbose=not args.quiet,
    )

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"DEDUPLICATION SUMMARY: {result.species_name}")
    print(f"{'=' * 60}")
    print(f"Total images:          {result.total_images}")
    print(f"Unique images:         {result.unique_images}")
    print(f"Duplicate groups:      {result.duplicate_groups}")
    print(f"Marked for deletion:   {result.duplicates_marked}")

    if result.errors:
        print(f"Errors:                {len(result.errors)}")

    if result.output_file:
        print(f"Output file:           {result.output_file}")

    print(f"{'=' * 60}\n")

    # Exit with appropriate code
    if result.errors and result.duplicates_marked == 0:
        sys.exit(1)

    sys.exit(0)


def embeddings_cli():
    """CLI for generating CNN embeddings."""
    parser = argparse.ArgumentParser(
        prog="plantnet-embeddings",
        description="Analyze image similarity using CNN features.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet-embeddings /path/to/species/Acacia_dealbata
  plantnet-embeddings /path/to/species/Acacia_dealbata --threshold 0.90
  plantnet-embeddings /path/to/species/Acacia_dealbata --model resnet50
        """,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Path to the species image directory",
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
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON file for results",
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
        import json

        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {args.output}")

    sys.exit(0)


def download_cli():
    """CLI for downloading images (placeholder for now)."""
    parser = argparse.ArgumentParser(
        prog="plantnet-download",
        description="Download images for a species.",
    )

    parser.add_argument("species", help="Species name")
    parser.add_argument("--limit", type=int, default=100, help="Max images to download")

    args = parser.parse_args()

    print(f"Downloading images for: {args.species}")
    print("Note: This command will be fully implemented in a future version.")
    print("For now, use: python scripts/images/batch_download_images.py")
    sys.exit(0)


if __name__ == "__main__":
    # For testing
    deduplicate_cli()
