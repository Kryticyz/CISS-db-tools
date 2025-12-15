#!/usr/bin/env python3
"""
Image deduplication module using perceptual hashing.

This module detects duplicate images within a directory using perceptual hashing
(pHash) which can identify similar images even with minor modifications like
resizing, compression, or color adjustments.

Can be used as a standalone script or imported as a module for the species pipeline.

Dependencies:
    pip install Pillow imagehash

Usage:
    # As standalone script
    python deduplicate_images.py /path/to/species/directory

    # As module
    from deduplicate_images import deduplicate_species_images
    result = deduplicate_species_images("/path/to/species/directory")
"""

import argparse
import hashlib
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

# Default hash size for perceptual hashing (higher = more precise but slower)
DEFAULT_HASH_SIZE = 16

# Default hamming distance threshold for considering images as duplicates
# Lower = stricter matching, Higher = more permissive
DEFAULT_HAMMING_THRESHOLD = 5


@dataclass
class DeduplicationResult:
    """Result of deduplication for a species directory."""

    species_name: str
    directory: Path
    total_images: int
    unique_images: int
    duplicate_groups: int
    duplicates_marked: int
    marked_for_deletion: List[str] = field(default_factory=list)
    duplicate_group_details: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[Tuple[str, str]] = field(default_factory=list)
    output_file: Optional[Path] = None

    @property
    def has_duplicates(self) -> bool:
        return self.duplicates_marked > 0

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization."""
        return {
            "species_name": self.species_name,
            "directory": str(self.directory),
            "total_images": self.total_images,
            "unique_images": self.unique_images,
            "duplicate_groups": self.duplicate_groups,
            "duplicates_marked": self.duplicates_marked,
            "marked_for_deletion": self.marked_for_deletion,
            "duplicate_group_details": self.duplicate_group_details,
            "errors": self.errors,
            "output_file": str(self.output_file) if self.output_file else None,
        }


def compute_image_hash(
    image_path: Path, hash_size: int = DEFAULT_HASH_SIZE, use_phash: bool = True
) -> Optional[Tuple[Path, str, Optional[str]]]:
    """
    Compute perceptual hash for a single image.

    Args:
        image_path: Path to the image file
        hash_size: Size of the hash (default 16)
        use_phash: If True, use perceptual hash; if False, use average hash

    Returns:
        Tuple of (image_path, hash_string, error_message) or None if import fails
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError as e:
        return (image_path, "", f"Missing dependency: {e}")

    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            if use_phash:
                img_hash = imagehash.phash(img, hash_size=hash_size)
            else:
                img_hash = imagehash.average_hash(img, hash_size=hash_size)

            return (image_path, str(img_hash), None)

    except Exception as e:
        return (image_path, "", f"Error processing image: {str(e)}")


def compute_file_hash(image_path: Path) -> Tuple[Path, str, Optional[str]]:
    """
    Compute MD5 hash of file contents for exact duplicate detection.

    Args:
        image_path: Path to the image file

    Returns:
        Tuple of (image_path, hash_string, error_message)
    """
    try:
        md5_hash = hashlib.md5()
        with open(image_path, "rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return (image_path, md5_hash.hexdigest(), None)
    except Exception as e:
        return (image_path, "", f"Error reading file: {str(e)}")


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hash strings.

    Args:
        hash1: First hash string (hex)
        hash2: Second hash string (hex)

    Returns:
        Hamming distance (number of differing bits)
    """
    try:
        import imagehash

        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except ImportError:
        # Fallback: simple hex comparison
        if len(hash1) != len(hash2):
            return max(len(hash1), len(hash2)) * 4

        distance = 0
        for c1, c2 in zip(hash1, hash2):
            diff = int(c1, 16) ^ int(c2, 16)
            distance += bin(diff).count("1")
        return distance


def find_duplicate_groups(
    hash_map: Dict[Path, str], hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD
) -> List[Set[Path]]:
    """
    Find groups of duplicate images based on hash similarity.

    Uses Union-Find algorithm for efficient grouping.

    Args:
        hash_map: Dictionary mapping image paths to their hashes
        hamming_threshold: Maximum Hamming distance to consider as duplicate

    Returns:
        List of sets, where each set contains paths of duplicate images
    """
    paths = list(hash_map.keys())
    n = len(paths)

    if n == 0:
        return []

    # Union-Find data structure
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px == py:
            return
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1

    # Compare all pairs and union similar images
    for i in range(n):
        for j in range(i + 1, n):
            hash_i = hash_map[paths[i]]
            hash_j = hash_map[paths[j]]

            # Skip if either hash is empty (error case)
            if not hash_i or not hash_j:
                continue

            distance = hamming_distance(hash_i, hash_j)
            if distance <= hamming_threshold:
                union(i, j)

    # Group paths by their root parent
    groups: Dict[int, Set[Path]] = defaultdict(set)
    for i, path in enumerate(paths):
        root = find(i)
        groups[root].add(path)

    # Return only groups with more than one image (actual duplicates)
    return [group for group in groups.values() if len(group) > 1]


def select_images_to_keep(duplicate_group: Set[Path]) -> Tuple[Path, List[Path]]:
    """
    Select which image to keep from a group of duplicates.

    Selection criteria (in order):
    1. Largest file size (likely highest quality)
    2. Alphabetically first filename (for determinism)

    Args:
        duplicate_group: Set of paths that are duplicates

    Returns:
        Tuple of (image_to_keep, list_of_images_to_delete)
    """
    # Sort by file size (descending) then by name (ascending) for determinism
    sorted_paths = sorted(duplicate_group, key=lambda p: (-p.stat().st_size, p.name))

    keep = sorted_paths[0]
    delete = sorted_paths[1:]

    return keep, delete


def get_image_files(directory: Path) -> List[Path]:
    """
    Get all image files in a directory.

    Args:
        directory: Path to the directory

    Returns:
        List of image file paths
    """
    image_files = []

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            image_files.append(file_path)

    return sorted(image_files)


def deduplicate_species_images(
    species_directory: Path | str,
    output_dir: Optional[Path | str] = None,
    hash_size: int = DEFAULT_HASH_SIZE,
    hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    max_workers: Optional[int] = None,
    use_file_hash: bool = False,
    verbose: bool = True,
) -> DeduplicationResult:
    """
    Detect and mark duplicate images in a species directory.

    This function:
    1. Computes perceptual hashes for all images
    2. Groups similar images together
    3. Marks duplicates for deletion (keeping one from each group)
    4. Writes a deletion list to a text file

    Args:
        species_directory: Path to the species image directory
        output_dir: Directory for output file (default: same as species_directory)
        hash_size: Size of perceptual hash (higher = more precise)
        hamming_threshold: Max Hamming distance for duplicates (0 = exact match only)
        max_workers: Number of parallel workers for hashing (default: CPU count)
        use_file_hash: If True, use MD5 file hash instead of perceptual hash
        verbose: If True, print progress information

    Returns:
        DeduplicationResult with details of duplicates found
    """
    species_directory = Path(species_directory)
    species_name = species_directory.name

    if output_dir is None:
        output_dir = species_directory
    else:
        output_dir = Path(output_dir)

    # Initialize result
    result = DeduplicationResult(
        species_name=species_name,
        directory=species_directory,
        total_images=0,
        unique_images=0,
        duplicate_groups=0,
        duplicates_marked=0,
    )

    # Check directory exists
    if not species_directory.exists():
        result.errors.append(("directory", f"Directory not found: {species_directory}"))
        return result

    if not species_directory.is_dir():
        result.errors.append(("directory", f"Not a directory: {species_directory}"))
        return result

    # Get all image files
    image_files = get_image_files(species_directory)
    result.total_images = len(image_files)

    if verbose:
        print(f"[{species_name}] Found {result.total_images} images")

    if result.total_images < 2:
        result.unique_images = result.total_images
        if verbose:
            print(f"[{species_name}] Not enough images to check for duplicates")
        return result

    # Compute hashes in parallel
    hash_map: Dict[Path, str] = {}

    if verbose:
        print(f"[{species_name}] Computing image hashes...")

    hash_func = compute_file_hash if use_file_hash else compute_image_hash

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        if use_file_hash:
            futures = {
                executor.submit(compute_file_hash, img): img for img in image_files
            }
        else:
            futures = {
                executor.submit(compute_image_hash, img, hash_size, True): img
                for img in image_files
            }

        for future in as_completed(futures):
            try:
                path, img_hash, error = future.result()
                if error:
                    result.errors.append((path.name, error))
                    if verbose:
                        print(f"[{species_name}] Warning: {path.name}: {error}")
                else:
                    hash_map[path] = img_hash
            except Exception as e:
                img_path = futures[future]
                result.errors.append((img_path.name, str(e)))
                if verbose:
                    print(f"[{species_name}] Error processing {img_path.name}: {e}")

    if verbose:
        print(f"[{species_name}] Successfully hashed {len(hash_map)} images")

    # Find duplicate groups
    if use_file_hash:
        # For file hashes, group by exact match
        hash_to_paths: Dict[str, Set[Path]] = defaultdict(set)
        for path, h in hash_map.items():
            hash_to_paths[h].add(path)
        duplicate_groups = [paths for paths in hash_to_paths.values() if len(paths) > 1]
    else:
        # For perceptual hashes, use Hamming distance
        duplicate_groups = find_duplicate_groups(hash_map, hamming_threshold)

    result.duplicate_groups = len(duplicate_groups)

    if verbose:
        print(f"[{species_name}] Found {result.duplicate_groups} duplicate groups")

    # Process duplicate groups and mark images for deletion
    for i, group in enumerate(duplicate_groups, 1):
        keep, delete = select_images_to_keep(group)

        # Record duplicate group details
        group_key = f"group_{i}"
        result.duplicate_group_details[group_key] = {
            "keep": keep.name,
            "delete": [p.name for p in delete],
            "total_in_group": len(group),
        }

        # Add to deletion list
        for path in delete:
            result.marked_for_deletion.append(path.name)

        result.duplicates_marked += len(delete)

    result.unique_images = result.total_images - result.duplicates_marked

    # Write deletion list to file
    if result.marked_for_deletion:
        output_file = output_dir / f"{species_name}_duplicates.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            f.write(f"# Duplicate images marked for deletion in {species_name}\n")
            f.write(f"# Total images: {result.total_images}\n")
            f.write(f"# Duplicates found: {result.duplicates_marked}\n")
            f.write(f"# Unique images: {result.unique_images}\n")
            f.write(f"# Duplicate groups: {result.duplicate_groups}\n")
            f.write("#\n")
            f.write("# Files listed below are marked for deletion.\n")
            f.write(
                "# One image from each duplicate group is kept (largest file size).\n"
            )
            f.write("#\n\n")

            for i, (group_key, details) in enumerate(
                result.duplicate_group_details.items(), 1
            ):
                f.write(f"# Group {i}: Keeping '{details['keep']}'\n")
                for filename in details["delete"]:
                    f.write(f"{filename}\n")
                f.write("\n")

        result.output_file = output_file

        if verbose:
            print(f"[{species_name}] Wrote deletion list to: {output_file}")

    if verbose:
        print(
            f"[{species_name}] Complete: {result.duplicates_marked} duplicates marked for deletion"
        )

    return result


def main():
    """Main function for standalone script execution."""
    parser = argparse.ArgumentParser(
        description="Detect duplicate images in a species directory using perceptual hashing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/species/Acacia_baileyana
  %(prog)s /path/to/species/Acacia_baileyana --threshold 3 --hash-size 8
  %(prog)s /path/to/species/Acacia_baileyana --exact  # Use MD5 for exact matches only
        """,
    )

    parser.add_argument(
        "directory", type=Path, help="Path to the species image directory"
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
        help=f"Hamming distance threshold for duplicates (default: {DEFAULT_HAMMING_THRESHOLD})",
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


if __name__ == "__main__":
    main()
