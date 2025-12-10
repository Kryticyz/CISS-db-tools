#!/usr/bin/env python3
"""
Unified query tool for GBIF and image counts databases.

This script queries both plantnet_gbif.db and plantnet_counts.db databases,
allowing for complex queries that aggregate and join data from both sources.

Species names are matched using underscore format (e.g., "Acacia_dealbata").

Usage:
    python query_unified_db.py --help
    python query_unified_db.py --summary
    python query_unified_db.py --species "Acacia_dealbata"
    python query_unified_db.py --compare-coverage
    python query_unified_db.py --top-combined 20
"""

import argparse
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple


def format_number(num):
    """Format number with commas."""
    if num is None:
        return "N/A"
    return f"{num:,}"


def truncate_text(text, max_length=50):
    """Truncate text to max_length with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def print_header(text, char="="):
    """Print a formatted header."""
    width = 80
    print()
    print(char * width)
    print(text.center(width))
    print(char * width)


def print_subheader(text, char="-"):
    """Print a formatted subheader."""
    print()
    print(text)
    print(char * len(text))


class UnifiedQueryTool:
    """Query tool for unified GBIF and counts databases."""

    def __init__(self, gbif_db="./plantnet_gbif.db", counts_db="./plantnet_counts.db"):
        """
        Initialize query tool.

        Args:
            gbif_db: Path to GBIF database
            counts_db: Path to counts database
        """
        self.gbif_db = gbif_db
        self.counts_db = counts_db

    def connect_gbif(self) -> sqlite3.Connection:
        """Connect to GBIF database."""
        return sqlite3.connect(self.gbif_db)

    def connect_counts(self) -> sqlite3.Connection:
        """Connect to counts database."""
        return sqlite3.connect(self.counts_db)

    def cmd_summary(self):
        """Display summary of both databases."""
        print_header("UNIFIED DATABASE SUMMARY")

        # GBIF stats
        print_subheader("GBIF Database")
        with self.connect_gbif() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM occurrences")
            occ_count = cursor.fetchone()[0]
            print(f"  Total occurrences: {format_number(occ_count)}")

            cursor.execute("SELECT COUNT(*) FROM multimedia")
            media_count = cursor.fetchone()[0]
            print(f"  Total multimedia records: {format_number(media_count)}")

            cursor.execute(
                "SELECT COUNT(DISTINCT species_normalized) FROM occurrences WHERE species_normalized IS NOT NULL"
            )
            species_count = cursor.fetchone()[0]
            print(f"  Unique species: {format_number(species_count)}")

            cursor.execute(
                "SELECT COUNT(DISTINCT countryCode) FROM occurrences WHERE countryCode IS NOT NULL"
            )
            country_count = cursor.fetchone()[0]
            print(f"  Unique countries: {format_number(country_count)}")

        # Counts stats
        print_subheader("Image Counts Database")
        with self.connect_counts() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM image_counts")
            dir_count = cursor.fetchone()[0]
            print(f"  Total directories: {format_number(dir_count)}")

            cursor.execute("SELECT SUM(original_count) FROM image_counts")
            orig_total = cursor.fetchone()[0] or 0
            print(f"  Total images (original): {format_number(orig_total)}")

            cursor.execute("SELECT SUM(checked_count) FROM image_counts")
            check_total = cursor.fetchone()[0] or 0
            print(f"  Total images (checked): {format_number(check_total)}")

        # Combined stats
        print_subheader("Combined Coverage")
        with self.connect_gbif() as gbif_conn, self.connect_counts() as counts_conn:
            gbif_cursor = gbif_conn.cursor()
            counts_cursor = counts_conn.cursor()

            # Get species from both
            gbif_cursor.execute(
                "SELECT DISTINCT species_normalized FROM occurrences WHERE species_normalized IS NOT NULL"
            )
            gbif_species = set(row[0] for row in gbif_cursor.fetchall())

            counts_cursor.execute("SELECT directory FROM image_counts")
            count_species = set(row[0] for row in counts_cursor.fetchall())

            both = gbif_species & count_species
            only_gbif = gbif_species - count_species
            only_counts = count_species - gbif_species

            print(f"  Species in both databases: {format_number(len(both))}")
            print(f"  Species only in GBIF: {format_number(len(only_gbif))}")
            print(f"  Species only in counts: {format_number(len(only_counts))}")

    def cmd_species(self, species_name: str, show_details: bool = False):
        """Search for a species in both databases."""
        print_header(f"SPECIES SEARCH: '{species_name}'")

        # Normalize species name (spaces to underscores)
        normalized = species_name.replace(" ", "_")

        # Search GBIF
        print_subheader("GBIF Observations")
        with self.connect_gbif() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT countryCode)
                FROM occurrences
                WHERE species_normalized LIKE ? OR acceptedScientificName_normalized LIKE ?
            """,
                (f"%{normalized}%", f"%{normalized}%"),
            )
            occ_count, country_count = cursor.fetchone()

            print(f"  Observations: {format_number(occ_count)}")
            print(f"  Countries: {format_number(country_count)}")

            if show_details and occ_count > 0:
                cursor.execute(
                    """
                    SELECT countryCode, COUNT(*) as count
                    FROM occurrences
                    WHERE species_normalized LIKE ? OR acceptedScientificName_normalized LIKE ?
                    GROUP BY countryCode
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (f"%{normalized}%", f"%{normalized}%"),
                )
                print("\n  Top countries:")
                for country, count in cursor.fetchall():
                    print(f"    {country}: {format_number(count)} observations")

        # Search counts
        print_subheader("Image Counts")
        with self.connect_counts() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT directory, original_count, checked_count, unchecked_count
                FROM image_counts
                WHERE directory LIKE ?
                ORDER BY original_count DESC
            """,
                (f"%{normalized}%",),
            )
            results = cursor.fetchall()

            if results:
                print(
                    f"  Found {len(results)} matching director{'y' if len(results) == 1 else 'ies'}"
                )
                print()
                print(
                    f"  {'Directory':<40} {'Original':>10} {'Checked':>10} {'Unchecked':>10}"
                )
                print("  " + "-" * 74)
                for directory, orig, check, uncheck in results[:10]:
                    print(
                        f"  {truncate_text(directory, 38):<40} {format_number(orig):>10} {format_number(check):>10} {format_number(uncheck):>10}"
                    )
                if len(results) > 10:
                    print(f"\n  ... and {len(results) - 10} more")
            else:
                print("  No matching directories found")

    def cmd_compare_coverage(self, limit: int = 50):
        """Compare coverage between GBIF and counts databases."""
        print_header("COVERAGE COMPARISON")

        with self.connect_gbif() as gbif_conn, self.connect_counts() as counts_conn:
            gbif_cursor = gbif_conn.cursor()
            counts_cursor = counts_conn.cursor()

            # Species in both
            print_subheader(f"Top {limit} Species in Both Databases")
            gbif_cursor.execute(
                """
                SELECT species_normalized, COUNT(*) as obs_count
                FROM occurrences
                WHERE species_normalized IS NOT NULL
                GROUP BY species_normalized
            """
            )
            gbif_data = {row[0]: row[1] for row in gbif_cursor.fetchall()}

            counts_cursor.execute(
                """
                SELECT directory, checked_count
                FROM image_counts
                WHERE checked_count IS NOT NULL
            """
            )
            counts_data = {row[0]: row[1] for row in counts_cursor.fetchall()}

            # Find species in both
            common_species = set(gbif_data.keys()) & set(counts_data.keys())

            combined = []
            for species in common_species:
                combined.append(
                    (
                        species,
                        gbif_data[species],
                        counts_data[species],
                        gbif_data[species] + counts_data[species],
                    )
                )

            combined.sort(key=lambda x: x[3], reverse=True)

            print(f"\nFound {len(common_species):,} species in both databases")
            print()
            print(
                f"{'Rank':<6} {'Species':<40} {'Observations':>13} {'Images':>10} {'Total':>10}"
            )
            print("-" * 85)

            for i, (species, obs, imgs, total) in enumerate(combined[:limit], 1):
                print(
                    f"{i:<6} {truncate_text(species, 38):<40} {obs:>13,} {imgs:>10,} {total:>10,}"
                )

            # Species only in GBIF
            print_subheader(f"Top {limit} Species Only in GBIF (no image directory)")
            only_gbif = [
                (species, count)
                for species, count in gbif_data.items()
                if species not in counts_data
            ]
            only_gbif.sort(key=lambda x: x[1], reverse=True)

            print(f"\nFound {len(only_gbif):,} species only in GBIF")
            if only_gbif:
                print()
                print(f"{'Rank':<6} {'Species':<55} {'Observations':>13}")
                print("-" * 80)
                for i, (species, count) in enumerate(only_gbif[:limit], 1):
                    print(f"{i:<6} {truncate_text(species, 53):<55} {count:>13,}")

            # Species only in counts
            print_subheader(f"Top {limit} Species Only in Counts (no GBIF records)")
            only_counts = [
                (species, count)
                for species, count in counts_data.items()
                if species not in gbif_data
            ]
            only_counts.sort(key=lambda x: x[1], reverse=True)

            print(f"\nFound {len(only_counts):,} species only in counts")
            if only_counts:
                print()
                print(f"{'Rank':<6} {'Species':<55} {'Images':>13}")
                print("-" * 80)
                for i, (species, count) in enumerate(only_counts[:limit], 1):
                    print(f"{i:<6} {truncate_text(species, 53):<55} {count:>13,}")

    def cmd_top_combined(self, n: int = 20, dataset: str = "checked"):
        """Show top species by combined metric (images + observations)."""
        print_header(f"TOP {n} SPECIES BY COMBINED METRIC")

        with self.connect_gbif() as gbif_conn, self.connect_counts() as counts_conn:
            gbif_cursor = gbif_conn.cursor()
            counts_cursor = counts_conn.cursor()

            # Get GBIF counts
            gbif_cursor.execute(
                """
                SELECT species_normalized, COUNT(*) as count
                FROM occurrences
                WHERE species_normalized IS NOT NULL
                GROUP BY species_normalized
            """
            )
            gbif_data = {row[0]: row[1] for row in gbif_cursor.fetchall()}

            # Get image counts
            count_field = f"{dataset}_count"
            counts_cursor.execute(
                f"""
                SELECT directory, {count_field}
                FROM image_counts
                WHERE {count_field} IS NOT NULL
            """
            )
            counts_data = {row[0]: row[1] for row in counts_cursor.fetchall()}

            # Combine
            all_species = set(gbif_data.keys()) | set(counts_data.keys())
            combined = []

            for species in all_species:
                obs = gbif_data.get(species, 0)
                imgs = counts_data.get(species, 0)
                total = obs + imgs

                combined.append((species, obs, imgs, total))

            combined.sort(key=lambda x: x[3], reverse=True)

            print(f"\nDataset: {dataset}")
            print(f"Total unique species: {len(all_species):,}")
            print()
            print(
                f"{'Rank':<6} {'Species':<40} {'Observations':>13} {'Images':>10} {'Total':>10}"
            )
            print("-" * 85)

            for i, (species, obs, imgs, total) in enumerate(combined[:n], 1):
                print(
                    f"{i:<6} {truncate_text(species, 38):<40} {obs:>13,} {imgs:>10,} {total:>10,}"
                )

    def cmd_country_species(self, country_code: str, limit: int = 20):
        """Show species observed in a country with their image counts."""
        print_header(f"SPECIES IN COUNTRY: {country_code}")

        with self.connect_gbif() as gbif_conn, self.connect_counts() as counts_conn:
            gbif_cursor = gbif_conn.cursor()
            counts_cursor = counts_conn.cursor()

            # Get species in country
            gbif_cursor.execute(
                """
                SELECT species_normalized, COUNT(*) as obs_count
                FROM occurrences
                WHERE countryCode = ? AND species_normalized IS NOT NULL
                GROUP BY species_normalized
                ORDER BY obs_count DESC
            """,
                (country_code,),
            )
            species_obs = gbif_cursor.fetchall()

            print(f"\nFound {len(species_obs):,} species in {country_code}")

            if not species_obs:
                return

            # Get image counts for these species
            counts_cursor.execute(
                """
                SELECT directory, checked_count
                FROM image_counts
                WHERE checked_count IS NOT NULL
            """
            )
            counts_data = {row[0]: row[1] for row in counts_cursor.fetchall()}

            print()
            print(
                f"{'Rank':<6} {'Species':<40} {'Observations':>13} {'Images':>10} {'Has Images':<12}"
            )
            print("-" * 87)

            for i, (species, obs_count) in enumerate(species_obs[:limit], 1):
                img_count = counts_data.get(species, 0)
                has_images = "✓" if img_count > 0 else "✗"
                print(
                    f"{i:<6} {truncate_text(species, 38):<40} {obs_count:>13,} {img_count:>10,} {has_images:<12}"
                )

            if len(species_obs) > limit:
                print(f"\n... and {len(species_obs) - limit:,} more species")

    def cmd_family_stats(self, family_name: str):
        """Show statistics for a plant family."""
        print_header(f"FAMILY STATISTICS: {family_name}")

        with self.connect_gbif() as gbif_conn, self.connect_counts() as counts_conn:
            gbif_cursor = gbif_conn.cursor()
            counts_cursor = counts_conn.cursor()

            # GBIF stats
            print_subheader("GBIF Data")
            gbif_cursor.execute(
                """
                SELECT COUNT(DISTINCT species_normalized), COUNT(*)
                FROM occurrences
                WHERE family LIKE ? AND species_normalized IS NOT NULL
            """,
                (f"%{family_name}%",),
            )
            species_count, obs_count = gbif_cursor.fetchone()

            print(f"  Unique species: {format_number(species_count)}")
            print(f"  Total observations: {format_number(obs_count)}")

            # Get species list
            gbif_cursor.execute(
                """
                SELECT species_normalized, COUNT(*) as count
                FROM occurrences
                WHERE family LIKE ? AND species_normalized IS NOT NULL
                GROUP BY species_normalized
                ORDER BY count DESC
            """,
                (f"%{family_name}%",),
            )
            gbif_species = {row[0]: row[1] for row in gbif_cursor.fetchall()}

            # Image counts for these species
            print_subheader("Image Counts")
            counts_cursor.execute(
                """
                SELECT directory, checked_count
                FROM image_counts
                WHERE checked_count IS NOT NULL
            """
            )
            counts_data = {row[0]: row[1] for row in counts_cursor.fetchall()}

            species_with_images = sum(
                1 for sp in gbif_species.keys() if sp in counts_data
            )
            total_images = sum(counts_data.get(sp, 0) for sp in gbif_species.keys())

            print(f"  Species with images: {format_number(species_with_images)}")
            print(f"  Total images: {format_number(total_images)}")

            # Top species
            print_subheader("Top Species in Family")
            combined = []
            for species in gbif_species.keys():
                obs = gbif_species[species]
                imgs = counts_data.get(species, 0)
                combined.append((species, obs, imgs))

            combined.sort(key=lambda x: x[1], reverse=True)

            print()
            print(f"{'Rank':<6} {'Species':<45} {'Observations':>13} {'Images':>10}")
            print("-" * 80)

            for i, (species, obs, imgs) in enumerate(combined[:20], 1):
                print(f"{i:<6} {truncate_text(species, 43):<45} {obs:>13,} {imgs:>10,}")

    def cmd_search_directory(self, pattern: str):
        """Search for directories/species by pattern."""
        print_header(f"DIRECTORY SEARCH: '{pattern}'")

        with self.connect_counts() as counts_conn, self.connect_gbif() as gbif_conn:
            counts_cursor = counts_conn.cursor()
            gbif_cursor = gbif_conn.cursor()

            # Search directories
            counts_cursor.execute(
                """
                SELECT directory, original_count, checked_count
                FROM image_counts
                WHERE directory LIKE ?
                ORDER BY checked_count DESC
            """,
                (f"%{pattern}%",),
            )
            directories = counts_cursor.fetchall()

            print(f"\nFound {len(directories):,} matching directories")

            if not directories:
                return

            print()
            print(
                f"{'Directory':<45} {'Original':>10} {'Checked':>10} {'GBIF Obs':>10}"
            )
            print("-" * 81)

            for directory, orig, check in directories[:50]:
                # Get GBIF count
                gbif_cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM occurrences
                    WHERE species_normalized = ?
                """,
                    (directory,),
                )
                gbif_count = gbif_cursor.fetchone()[0]

                print(
                    f"{truncate_text(directory, 43):<45} {format_number(orig):>10} {format_number(check):>10} {format_number(gbif_count):>10}"
                )

            if len(directories) > 50:
                print(f"\n... and {len(directories) - 50:,} more")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query unified GBIF and counts databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summary of both databases
  %(prog)s --summary

  # Search for a species
  %(prog)s --species "Acacia_dealbata"
  %(prog)s --species "Quercus" --details

  # Compare coverage
  %(prog)s --compare-coverage
  %(prog)s --compare-coverage --limit 100

  # Top species by combined metric
  %(prog)s --top-combined 30
  %(prog)s --top-combined 50 --dataset original

  # Species in a country
  %(prog)s --country FR --limit 30

  # Family statistics
  %(prog)s --family Fabaceae

  # Search directories
  %(prog)s --search "Acacia"
        """,
    )

    # Commands
    parser.add_argument(
        "--summary", action="store_true", help="Display summary of both databases"
    )
    parser.add_argument(
        "--species", metavar="NAME", help="Search for species in both databases"
    )
    parser.add_argument(
        "--compare-coverage",
        action="store_true",
        help="Compare coverage between databases",
    )
    parser.add_argument(
        "--top-combined",
        type=int,
        metavar="N",
        help="Show top N species by combined metric",
    )
    parser.add_argument(
        "--country",
        metavar="CODE",
        help="Show species in country with image counts",
    )
    parser.add_argument(
        "--family", metavar="NAME", help="Show statistics for a plant family"
    )
    parser.add_argument(
        "--search", metavar="PATTERN", help="Search directories by pattern"
    )

    # Options
    parser.add_argument(
        "--details", action="store_true", help="Show additional details"
    )
    parser.add_argument(
        "--limit", type=int, default=50, metavar="N", help="Limit results (default: 50)"
    )
    parser.add_argument(
        "--dataset",
        choices=["original", "checked", "unchecked"],
        default="checked",
        help="Dataset for counts (default: checked)",
    )
    parser.add_argument(
        "--gbif-db",
        default="./plantnet_gbif.db",
        help="Path to GBIF database (default: ./plantnet_gbif.db)",
    )
    parser.add_argument(
        "--counts-db",
        default="./plantnet_counts.db",
        help="Path to counts database (default: ./plantnet_counts.db)",
    )

    args = parser.parse_args()

    # Check if any command was specified
    if not any(
        [
            args.summary,
            args.species,
            args.compare_coverage,
            args.top_combined,
            args.country,
            args.family,
            args.search,
        ]
    ):
        parser.print_help()
        return

    # Initialize query tool
    tool = UnifiedQueryTool(gbif_db=args.gbif_db, counts_db=args.counts_db)

    try:
        if args.summary:
            tool.cmd_summary()

        if args.species:
            tool.cmd_species(args.species, args.details)

        if args.compare_coverage:
            tool.cmd_compare_coverage(args.limit)

        if args.top_combined:
            tool.cmd_top_combined(args.top_combined, args.dataset)

        if args.country:
            tool.cmd_country_species(args.country, args.limit)

        if args.family:
            tool.cmd_family_stats(args.family)

        if args.search:
            tool.cmd_search_directory(args.search)

        print()  # Final newline

    except sqlite3.OperationalError as e:
        print(f"\nError: Database not found or invalid", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        print("\nMake sure to create databases first:", file=sys.stderr)
        print("  python src/parse_gbif_db.py --create", file=sys.stderr)
        print("  python src/parse_counts_db.py --create", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
