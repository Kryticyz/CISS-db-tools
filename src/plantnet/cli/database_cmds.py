"""
Database command-line interfaces.

Provides CLI wrappers for database building and querying operations.
"""

import argparse
import sys

from plantnet.core import GBIFParser


def query_cli():
    """CLI for querying databases."""
    parser = argparse.ArgumentParser(
        prog="plantnet-db-query",
        description="Query GBIF and counts databases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet-db-query --summary
  plantnet-db-query --species "Acacia dealbata"
  plantnet-db-query --list-species

Note: For more advanced queries, use the Python scripts directly:
  python scripts/database/query_unified_db.py
  python scripts/database/query_gbif.py
        """,
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show database summary statistics",
    )

    parser.add_argument(
        "--species",
        type=str,
        help="Search for a specific species",
    )

    parser.add_argument(
        "--list-species",
        action="store_true",
        help="List all species in database",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of results (default: 10)",
    )

    args = parser.parse_args()

    # Determine what to do
    if args.summary:
        print("Database Summary")
        print("=" * 60)
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/database/query_unified_db.py --summary")
        sys.exit(0)

    if args.species:
        print(f"Searching for species: {args.species}")
        print("\nNote: Full implementation coming soon.")
        print(
            f"For now, use: python scripts/database/query_unified_db.py --species '{args.species}'"
        )
        sys.exit(0)

    if args.list_species:
        print("Listing all species...")
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/database/query_unified_db.py --top-species")
        sys.exit(0)

    # No arguments provided
    parser.print_help()
    sys.exit(0)


def build_cli():
    """CLI for building databases."""
    parser = argparse.ArgumentParser(
        prog="plantnet-db-build",
        description="Build databases from raw GBIF data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet-db-build --create
  plantnet-db-build --create --max-rows 10000

Note: For full control, use the Python scripts directly:
  python scripts/data_processing/parse_gbif_db.py --create
  python scripts/data_processing/parse_counts_db.py --create
        """,
    )

    parser.add_argument(
        "--create",
        action="store_true",
        help="Create new database (overwrites existing)",
    )

    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum rows to process (for testing)",
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Show database information",
    )

    args = parser.parse_args()

    if args.create:
        print("Building GBIF database...")
        print("=" * 60)
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/data_processing/parse_gbif_db.py --create")
        if args.max_rows:
            print(f"       Add --max-rows {args.max_rows} for testing")
        sys.exit(0)

    if args.info:
        print("Database Information")
        print("=" * 60)
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/data_processing/parse_gbif_db.py --info")
        sys.exit(0)

    # No arguments provided
    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    # For testing
    query_cli()
