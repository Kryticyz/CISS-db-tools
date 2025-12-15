#!/usr/bin/env python3
"""
Query script to find species with counts less than 400 in the cleaned dataset
and check how many images exist for them in the GBIF database.

This script queries both the plantnet_counts.db and plantnet_gbif.db databases
to compare local image counts with GBIF image availability.

Usage:
    python src/query_low_count_species.py
    python src/query_low_count_species.py --threshold 500
    python src/query_low_count_species.py --dataset unchecked
    python src/query_low_count_species.py --output results.csv
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def format_number(num):
    """Format number with commas."""
    if num is None:
        return "N/A"
    return f"{num:,}"


def print_header(text, char="="):
    """Print a formatted header."""
    width = 90
    print()
    print(char * width)
    print(text.center(width))
    print(char * width)
    print()


def print_subheader(text, char="-"):
    """Print a formatted subheader."""
    print()
    print(text)
    print(char * len(text))


def get_low_count_species(
    counts_db: str, threshold: int, dataset: str = "checked"
) -> List[Tuple[str, int]]:
    """
    Find all species with counts below the threshold in the specified dataset.

    Args:
        counts_db: Path to counts database
        threshold: Maximum count threshold (exclusive)
        dataset: Which dataset to use (checked, unchecked, or original)

    Returns:
        List of (species_name, count) tuples
    """
    column_map = {
        "checked": "checked_count",
        "unchecked": "unchecked_count",
        "original": "original_count",
    }

    if dataset not in column_map:
        raise ValueError(
            f"Invalid dataset: {dataset}. Must be one of {list(column_map.keys())}"
        )

    column = column_map[dataset]

    conn = sqlite3.connect(counts_db)
    cursor = conn.cursor()

    query = f"""
        SELECT directory, {column}
        FROM image_counts
        WHERE {column} IS NOT NULL
          AND {column} < ?
        ORDER BY {column} DESC, directory ASC
    """

    cursor.execute(query, (threshold,))
    results = cursor.fetchall()
    conn.close()

    return results


def get_gbif_image_counts(gbif_db: str, species_list: List[str]) -> Dict[str, int]:
    """
    Get GBIF image counts for a list of species.

    Args:
        gbif_db: Path to GBIF database
        species_list: List of species names (normalized, e.g., 'Genus_species')

    Returns:
        Dictionary mapping species_name to image count
    """
    conn = sqlite3.connect(gbif_db)
    cursor = conn.cursor()

    results = {}

    for species in species_list:
        query = """
            SELECT COUNT(DISTINCT m.id) as image_count
            FROM multimedia m
            INNER JOIN occurrences o ON m.gbifID = o.gbifID
            WHERE o.species_normalized = ?
              AND m.type = 'StillImage'
        """

        cursor.execute(query, (species,))
        count = cursor.fetchone()[0]
        results[species] = count

    conn.close()
    return results


def analyze_low_count_species(
    counts_db="./data/databases/plantnet_counts.db",
    gbif_db="./data/databases/plantnet_gbif.db",
    threshold=400,
    dataset="checked",
    output_file=None,
):
    """
    Main analysis function.

    Args:
        counts_db: Path to counts database
        gbif_db: Path to GBIF database
        threshold: Maximum count threshold
        dataset: Which count dataset to use
        output_file: Optional CSV output file path
    """

    print_header(f"SPECIES WITH {dataset.upper()} COUNT < {threshold}")

    # Check if databases exist
    if not Path(counts_db).exists():
        print(f"Error: Counts database not found: {counts_db}", file=sys.stderr)
        sys.exit(1)

    if not Path(gbif_db).exists():
        print(f"Error: GBIF database not found: {gbif_db}", file=sys.stderr)
        sys.exit(1)

    # Get low count species from counts database
    print("\n[1/3] Querying counts database...")
    low_count_species = get_low_count_species(counts_db, threshold, dataset)

    if not low_count_species:
        print(f"\nNo species found with {dataset} count < {threshold}")
        return

    print(f"Found {len(low_count_species)} species with {dataset} count < {threshold}")

    # Get GBIF image counts for these species
    print("\n[2/3] Querying GBIF database for image counts...")
    species_names = [species for species, _ in low_count_species]
    gbif_counts = get_gbif_image_counts(gbif_db, species_names)

    # Combine results
    print("\n[3/3] Combining results...")
    combined_results = []

    for species, local_count in low_count_species:
        gbif_count = gbif_counts.get(species, 0)
        combined_results.append((species, local_count, gbif_count))

    # Display results
    print_subheader("RESULTS")

    print(
        f"\n{'Rank':<6} {'Species':<45} {dataset.capitalize() + ' Count':>15} {'GBIF Images':>15} {'Difference':>15}"
    )
    print("-" * 100)

    for i, (species, local_count, gbif_count) in enumerate(combined_results, 1):
        difference = gbif_count - local_count
        diff_str = (
            f"+{format_number(difference)}"
            if difference > 0
            else format_number(difference)
        )
        print(
            f"{i:<6} {species:<45} {format_number(local_count):>15} {format_number(gbif_count):>15} {diff_str:>15}"
        )

    # Summary statistics
    print_subheader("SUMMARY STATISTICS")

    total_local = sum(count for _, count, _ in combined_results)
    total_gbif = sum(count for _, _, count in combined_results)
    species_with_more_gbif = sum(
        1 for _, local, gbif in combined_results if gbif > local
    )
    species_with_same = sum(1 for _, local, gbif in combined_results if gbif == local)
    species_with_less_gbif = sum(
        1 for _, local, gbif in combined_results if gbif < local
    )
    species_with_gbif_images = sum(1 for _, _, gbif in combined_results if gbif > 0)
    species_without_gbif = sum(1 for _, _, gbif in combined_results if gbif == 0)

    print(f"\nTotal species analyzed: {len(combined_results)}")
    print(f"Total local {dataset} images: {format_number(total_local)}")
    print(f"Total GBIF images: {format_number(total_gbif)}")
    print(f"Net difference: {format_number(total_gbif - total_local)}")
    print()
    print(
        f"Species with more images in GBIF: {species_with_more_gbif} ({species_with_more_gbif / len(combined_results) * 100:.1f}%)"
    )
    print(
        f"Species with same count: {species_with_same} ({species_with_same / len(combined_results) * 100:.1f}%)"
    )
    print(
        f"Species with fewer images in GBIF: {species_with_less_gbif} ({species_with_less_gbif / len(combined_results) * 100:.1f}%)"
    )
    print()
    print(
        f"Species with GBIF images available: {species_with_gbif_images} ({species_with_gbif_images / len(combined_results) * 100:.1f}%)"
    )
    print(
        f"Species without any GBIF images: {species_without_gbif} ({species_without_gbif / len(combined_results) * 100:.1f}%)"
    )

    # Top opportunities (most additional images in GBIF)
    print_subheader("TOP 20 OPPORTUNITIES (Most Additional Images in GBIF)")

    opportunities = [
        (species, local, gbif, gbif - local)
        for species, local, gbif in combined_results
        if gbif > local
    ]
    opportunities.sort(key=lambda x: x[3], reverse=True)

    if opportunities:
        print(
            f"\n{'Rank':<6} {'Species':<45} {'Local':>10} {'GBIF':>10} {'Additional':>15}"
        )
        print("-" * 90)
        for i, (species, local, gbif, additional) in enumerate(opportunities[:20], 1):
            print(
                f"{i:<6} {species:<45} {format_number(local):>10} {format_number(gbif):>10} {format_number(additional):>15}"
            )
    else:
        print("\nNo species found with more images in GBIF than locally.")

    # Species with no GBIF images
    if species_without_gbif > 0:
        print_subheader(f"SPECIES WITH NO GBIF IMAGES ({species_without_gbif} total)")

        no_gbif = [
            (species, local) for species, local, gbif in combined_results if gbif == 0
        ]
        no_gbif.sort(key=lambda x: x[1], reverse=True)

        print(f"\n{'Rank':<6} {'Species':<55} {'Local Count':>15}")
        print("-" * 80)
        for i, (species, local) in enumerate(no_gbif[:20], 1):
            print(f"{i:<6} {species:<55} {format_number(local):>15}")

        if len(no_gbif) > 20:
            print(f"\n... and {len(no_gbif) - 20} more species without GBIF images")

    # Export to CSV if requested
    if output_file:
        print_subheader(f"EXPORTING TO CSV: {output_file}")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Species",
                    f"{dataset.capitalize()}_Count",
                    "GBIF_Images",
                    "Difference",
                    "Has_GBIF_Images",
                ]
            )

            for species, local_count, gbif_count in combined_results:
                difference = gbif_count - local_count
                has_gbif = "Yes" if gbif_count > 0 else "No"
                writer.writerow(
                    [species, local_count, gbif_count, difference, has_gbif]
                )

        print(f"\nSuccessfully exported {len(combined_results)} rows to {output_file}")

    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Find species with low image counts and compare with GBIF availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find species with checked count < 400 (default)
  %(prog)s

  # Find species with unchecked count < 500
  %(prog)s --threshold 500 --dataset unchecked

  # Export results to CSV
  %(prog)s --output low_count_species.csv

  # Use custom database paths
  %(prog)s --counts-db ./my_counts.db --gbif-db ./my_gbif.db
        """,
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=400,
        help="Maximum count threshold (exclusive, default: 400)",
    )

    parser.add_argument(
        "--dataset",
        choices=["original", "checked", "unchecked"],
        default="checked",
        help="Which count dataset to use (default: checked)",
    )

    parser.add_argument(
        "--counts-db",
        default="./data/databases/plantnet_counts.db",
        help="Path to counts database (default: ./data/databases/plantnet_counts.db)",
    )

    parser.add_argument(
        "--gbif-db",
        default="./data/databases/plantnet_gbif.db",
        help="Path to GBIF database (default: ./data/databases/plantnet_gbif.db)",
    )

    parser.add_argument("--output", "-o", help="Export results to CSV file")

    args = parser.parse_args()

    try:
        analyze_low_count_species(
            counts_db=args.counts_db,
            gbif_db=args.gbif_db,
            threshold=args.threshold,
            dataset=args.dataset,
            output_file=args.output,
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
