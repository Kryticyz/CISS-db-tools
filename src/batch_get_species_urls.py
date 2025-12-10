#!/usr/bin/env python3
"""
Script to batch fetch GBIF URLs for multiple species from a list.
Processes each species and creates URL files, tracking species without images.
"""

import argparse
import sys
import time
from pathlib import Path

# Import functions from get_species_urls module
try:
    from get_species_urls import get_species_urls, normalize_species_name
except ImportError:
    print("Error: Cannot import get_species_urls module.")
    print(
        "Make sure get_species_urls.py is in the same directory or in your Python path."
    )
    sys.exit(1)


def read_species_from_file(filepath):
    """
    Read species names from a text file, one per line.
    Skips empty lines and lines starting with #.

    Args:
        filepath: Path to the text file containing species names

    Returns:
        List of species names
    """
    species_list = []
    try:
        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                species_list.append(line)

        return species_list
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def sanitize_filename(species_name):
    """
    Convert species name to a safe filename.

    Args:
        species_name: Species name (e.g., "Acacia_dealbata")

    Returns:
        Safe filename without special characters
    """
    # Replace any remaining spaces or special characters
    safe_name = species_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return safe_name


def process_species(
    species_name, db_path, output_dir, limit=400, prefer_country="AU", verbose=True
):
    """
    Process a single species: fetch URLs or mark as not found.

    Args:
        species_name: Name of the species
        db_path: Path to GBIF database
        output_dir: Directory to save URL files
        limit: Maximum URLs to fetch
        prefer_country: Country code to prefer
        verbose: Print detailed progress

    Returns:
        Tuple of (success, num_urls, error_message)
    """
    try:
        if verbose:
            print(f"\nProcessing: {species_name}")

        # Try to get URLs
        urls = get_species_urls(
            species_name, db_path=db_path, limit=limit, prefer_country=prefer_country
        )

        if not urls:
            if verbose:
                print(f"  ✗ No images found")
            return (False, 0, "No images found in database")

        # Save URLs to file
        safe_name = sanitize_filename(species_name)
        output_file = output_dir / f"{safe_name}_urls.txt"

        with open(output_file, "w") as f:
            for url_info in urls:
                f.write(url_info["url"] + "\n")

        if verbose:
            print(f"  ✓ Found {len(urls)} URLs → {output_file.name}")

        return (True, len(urls), None)

    except ValueError as e:
        # Species not found in database
        if verbose:
            print(f"  ✗ Not found in database")
        return (False, 0, str(e))
    except Exception as e:
        # Other errors
        if verbose:
            print(f"  ✗ Error: {e}")
        return (False, 0, str(e))


def batch_process_species(
    species_list,
    db_path="./plantnet_gbif.db",
    output_dir="./species_urls",
    no_images_file="./no_images.txt",
    limit=400,
    prefer_country="AU",
    verbose=True,
):
    """
    Process multiple species from a list.

    Args:
        species_list: List of species names
        db_path: Path to GBIF database
        output_dir: Directory to save URL files
        no_images_file: File to save species without images
        limit: Maximum URLs per species
        prefer_country: Country code to prefer
        verbose: Print detailed progress

    Returns:
        Dictionary with processing statistics
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(species_list)
    successful = []
    failed = []

    print(f"\n{'=' * 70}")
    print(f"Batch Processing {total} Species")
    print(f"{'=' * 70}")
    print(f"GBIF Database: {db_path}")
    print(f"Output directory: {output_dir}")
    print(f"Failed species file: {no_images_file}")
    print(f"URL limit per species: {limit}")
    print(f"Preferred country: {prefer_country}")
    print(f"{'=' * 70}\n")

    start_time = time.time()

    # Process each species
    for i, species_name in enumerate(species_list, 1):
        print(f"[{i}/{total}] ", end="")
        success, num_urls, error = process_species(
            species_name,
            db_path=db_path,
            output_dir=output_dir,
            limit=limit,
            prefer_country=prefer_country,
            verbose=verbose,
        )

        if success:
            successful.append((species_name, num_urls))
        else:
            failed.append((species_name, error))

    end_time = time.time()
    duration = end_time - start_time

    # Save failed species to file
    if failed:
        with open(no_images_file, "w") as f:
            f.write("# Species without images in GBIF database\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(failed)} species\n\n")
            for species, error in failed:
                f.write(f"{species}\n")
                f.write(f"# Error: {error}\n")

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"Processing Complete!")
    print(f"{'=' * 70}")
    print(f"Total species: {total}")
    print(f"Successful: {len(successful)} ({len(successful) / total * 100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed) / total * 100:.1f}%)")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Average: {duration / total:.2f} seconds per species")

    if successful:
        total_urls = sum(num for _, num in successful)
        print(f"Total URLs collected: {total_urls}")
        print(
            f"Average URLs per successful species: {total_urls / len(successful):.1f}"
        )

    print(f"{'=' * 70}\n")

    if failed:
        print(f"Species without images saved to: {no_images_file}")
        print(f"\nTop 10 failed species:")
        for species, error in failed[:10]:
            print(f"  ✗ {species}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
        print()

    return {
        "total": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_list": successful,
        "failure_list": failed,
        "duration": duration,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Batch fetch GBIF URLs for multiple species from a list file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process species_list.txt and save URLs to species_urls directory
  python src/batch_get_species_urls.py species_list.txt

  # Custom output directory
  python src/batch_get_species_urls.py species_list.txt --output ./my_urls

  # Get 200 URLs per species instead of 400
  python src/batch_get_species_urls.py species_list.txt --limit 200

  # Prefer images from France
  python src/batch_get_species_urls.py species_list.txt --country FR

  # Custom database path
  python src/batch_get_species_urls.py species_list.txt --db-path ./my_gbif.db

  # Save failed species to custom file
  python src/batch_get_species_urls.py species_list.txt --no-images failed.txt

  # Process only first 10 species (for testing)
  python src/batch_get_species_urls.py species_list.txt --max-species 10
        """,
    )

    parser.add_argument(
        "species_file",
        help="Text file containing species names (one per line, e.g., Acacia_dealbata)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./species_urls",
        help="Output directory for URL files (default: ./species_urls)",
    )
    parser.add_argument(
        "--no-images",
        default="./no_images.txt",
        help="Output file for species without images (default: ./no_images.txt)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=400,
        help="Maximum URLs per species (default: 400)",
    )
    parser.add_argument(
        "--country",
        default="AU",
        help="Country code to prefer (default: AU for Australia)",
    )
    parser.add_argument(
        "--db-path",
        default="./plantnet_gbif.db",
        help="Path to GBIF database (default: ./plantnet_gbif.db)",
    )
    parser.add_argument(
        "--max-species",
        type=int,
        help="Maximum number of species to process (for testing)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress detailed progress output",
    )

    args = parser.parse_args()

    # Check if database exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Please run 'python src/parse_gbif_db.py --create' first.")
        sys.exit(1)

    # Read species list
    print(f"Reading species from: {args.species_file}")
    species_list = read_species_from_file(args.species_file)

    if not species_list:
        print("Error: No species found in file")
        sys.exit(1)

    print(f"Found {len(species_list)} species")

    # Apply limit if specified
    if args.max_species:
        species_list = species_list[: args.max_species]
        print(f"Limiting to first {len(species_list)} species")

    # Process all species
    results = batch_process_species(
        species_list,
        db_path=args.db_path,
        output_dir=args.output,
        no_images_file=args.no_images,
        limit=args.limit,
        prefer_country=args.country,
        verbose=not args.quiet,
    )

    # Exit with error code if any species failed (optional)
    # Commented out since some failures are expected
    # if results["failed"] > 0:
    #     sys.exit(1)


if __name__ == "__main__":
    main()
