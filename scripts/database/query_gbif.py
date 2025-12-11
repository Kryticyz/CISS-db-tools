#!/usr/bin/env python3
"""
Interactive CLI tool for querying GBIF PlantNet data.

This script provides a command-line interface for querying and analyzing
the GBIF multimedia and occurrence data.

Usage:
    python query_gbif.py --help
    python query_gbif.py --summary
    python query_gbif.py --species "Acacia dealbata"
    python query_gbif.py --country FR --top-species 20
    python query_gbif.py --user "john" --count
    python query_gbif.py --observation 2644196009
    python query_gbif.py --date-range 2019-10-01 2019-10-31
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add scripts/data_processing to path to import parse_gbif
sys.path.insert(0, str(Path(__file__).parent.parent / "data_processing"))
from parse_gbif import GBIFParser


def print_header(text, char="="):
    """Print a formatted header."""
    width = 80
    print()
    print(char * width)
    print(text.center(width))
    print(char * width)


def print_subheader(text, char="-"):
    """Print a formatted subheader."""
    width = 80
    print()
    print(text)
    print(char * len(text))


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


def cmd_summary(parser):
    """Display summary of the dataset."""
    parser.print_summary()


def cmd_species(parser, species_name, show_images=False, limit=None):
    """Search for observations by species name."""
    print_header(f"SPECIES SEARCH: '{species_name}'")

    results = parser.search_by_species(species_name)

    if not results:
        print(f"\nNo observations found for species matching '{species_name}'")
        return

    print(f"\nFound {len(results):,} observations matching '{species_name}'")

    # Apply limit
    display_results = results[:limit] if limit else results

    print()
    print(f"{'#':<5} {'GBIF ID':<15} {'Species':<40} {'Country':<8} {'Date':<12}")
    print("-" * 80)

    for i, obs in enumerate(display_results, 1):
        gbif_id = obs.get("gbifID", "")
        scientific_name = truncate_text(obs.get("scientificName", ""), 38)
        country = obs.get("countryCode", "")
        event_date = obs.get("eventDate", "")
        date_str = event_date.split("T")[0] if event_date else ""

        print(f"{i:<5} {gbif_id:<15} {scientific_name:<40} {country:<8} {date_str:<12}")

        if show_images:
            images = parser.get_images_by_gbif_id(gbif_id)
            if images:
                for img in images:
                    img_type = img.get("title", "")
                    print(f"      ↳ {truncate_text(img_type, 70)}")

    if limit and len(results) > limit:
        print(
            f"\n... and {len(results) - limit:,} more results (use --limit to see more)"
        )

    print()
    print(f"Total: {len(results):,} observations")


def cmd_country(parser, country_code, top_species=None, show_details=False):
    """Search observations by country."""
    print_header(f"COUNTRY SEARCH: {country_code}")

    results = parser.search_by_country(country_code)

    if not results:
        print(f"\nNo observations found for country '{country_code}'")
        return

    print(f"\nFound {len(results):,} observations in {country_code}")

    if top_species:
        print_subheader(f"Top {top_species} Species in {country_code}")

        species_counts = {}
        for obs in results:
            species = obs.get("scientificName")
            if species:
                species_counts[species] = species_counts.get(species, 0) + 1

        sorted_species = sorted(
            species_counts.items(), key=lambda x: x[1], reverse=True
        )

        for i, (species, count) in enumerate(sorted_species[:top_species], 1):
            print(f"  {i:3d}. {species:<55} {count:>8,} obs")

    if show_details:
        print_subheader("Sample Observations")
        for i, obs in enumerate(results[:10], 1):
            gbif_id = obs.get("gbifID", "")
            scientific_name = obs.get("scientificName", "")
            date = (
                obs.get("eventDate", "").split("T")[0] if obs.get("eventDate") else ""
            )
            location = obs.get("locality", "") or obs.get("stateProvince", "")

            print(f"\n  {i}. GBIF ID: {gbif_id}")
            print(f"     Species: {scientific_name}")
            print(f"     Date: {date}")
            print(f"     Location: {truncate_text(location, 60)}")


def cmd_user(parser, username, show_count=False, limit=None):
    """Search images by user/creator."""
    print_header(f"USER SEARCH: '{username}'")

    results = parser.search_by_user(username)

    if not results:
        print(f"\nNo images found for user matching '{username}'")
        return

    print(f"\nFound {len(results):,} images by users matching '{username}'")

    if show_count:
        # Count by creator
        user_counts = {}
        for img in results:
            creator = img.get("creator", "")
            user_counts[creator] = user_counts.get(creator, 0) + 1

        print_subheader("Images by User")
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (user, count) in enumerate(sorted_users, 1):
            print(f"  {i:3d}. {user:<55} {count:>8,} images")
    else:
        # Show individual images
        display_results = results[:limit] if limit else results[:50]

        print()
        print(f"{'#':<5} {'GBIF ID':<15} {'Creator':<30} {'Image Type':<25}")
        print("-" * 80)

        for i, img in enumerate(display_results, 1):
            gbif_id = img.get("gbifID", "")
            creator = truncate_text(img.get("creator", ""), 28)
            img_type = truncate_text(img.get("title", ""), 23)

            print(f"{i:<5} {gbif_id:<15} {creator:<30} {img_type:<25}")

        if len(results) > len(display_results):
            print(
                f"\n... and {len(results) - len(display_results):,} more images (use --limit to see more)"
            )


def cmd_observation(parser, gbif_id, show_images=True):
    """Show complete observation details."""
    print_header(f"OBSERVATION DETAILS: GBIF ID {gbif_id}")

    observation = parser.get_complete_observation(gbif_id)

    occurrence = observation["occurrence"]
    multimedia = observation["multimedia"]

    if not occurrence:
        print(f"\nNo occurrence record found for GBIF ID {gbif_id}")
        return

    # Basic information
    print_subheader("Basic Information")
    print(f"  GBIF ID: {occurrence.get('gbifID')}")
    print(f"  Scientific Name: {occurrence.get('scientificName')}")
    print(f"  Common Name: {occurrence.get('vernacularName', 'N/A')}")
    print(f"  Basis of Record: {occurrence.get('basisOfRecord')}")
    print(f"  Occurrence Status: {occurrence.get('occurrenceStatus')}")

    # Taxonomy
    print_subheader("Taxonomy")
    print(f"  Kingdom: {occurrence.get('kingdom')}")
    print(f"  Phylum: {occurrence.get('phylum')}")
    print(f"  Class: {occurrence.get('class')}")
    print(f"  Order: {occurrence.get('order')}")
    print(f"  Family: {occurrence.get('family')}")
    print(f"  Genus: {occurrence.get('genus')}")
    print(f"  Species: {occurrence.get('species')}")

    # Location
    print_subheader("Location")
    print(f"  Country: {occurrence.get('countryCode')}")
    print(f"  State/Province: {occurrence.get('stateProvince')}")
    print(f"  Locality: {occurrence.get('locality')}")
    print(f"  Latitude: {occurrence.get('decimalLatitude')}")
    print(f"  Longitude: {occurrence.get('decimalLongitude')}")
    print(
        f"  Coordinate Uncertainty: {occurrence.get('coordinateUncertaintyInMeters')} m"
    )
    print(f"  Elevation: {occurrence.get('elevation')} m")

    # Temporal
    print_subheader("Temporal Information")
    print(f"  Event Date: {occurrence.get('eventDate')}")
    print(f"  Year: {occurrence.get('year')}")
    print(f"  Month: {occurrence.get('month')}")
    print(f"  Day: {occurrence.get('day')}")

    # Observer
    print_subheader("Observer/Recorder")
    print(f"  Recorded By: {occurrence.get('recordedBy')}")
    print(f"  Individual Count: {occurrence.get('individualCount')}")

    # Reference
    print_subheader("Reference")
    print(f"  References: {occurrence.get('references')}")
    print(f"  License: {occurrence.get('license')}")

    # Multimedia
    if show_images and multimedia:
        print_subheader(f"Multimedia ({len(multimedia)} images)")
        for i, img in enumerate(multimedia, 1):
            print(f"\n  Image {i}:")
            print(f"    Type: {img.get('title')}")
            print(f"    Format: {img.get('format')}")
            print(f"    URL: {img.get('identifier')}")
            print(f"    Creator: {img.get('creator')}")
            print(f"    Created: {img.get('created')}")
            print(f"    License: {img.get('license')}")
    elif not multimedia:
        print_subheader("Multimedia")
        print("  No multimedia records found")


def cmd_date_range(parser, start_date, end_date, count_only=False):
    """Filter observations by date range."""
    print_header(f"DATE RANGE: {start_date} to {end_date}")

    results = parser.filter_by_date_range(start_date, end_date)

    print(f"\nFound {len(results):,} observations in date range")

    if count_only:
        return

    # Show summary statistics
    if results:
        species_counts = {}
        country_counts = {}

        for obs in results:
            species = obs.get("scientificName")
            country = obs.get("countryCode")

            if species:
                species_counts[species] = species_counts.get(species, 0) + 1
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

        print_subheader("Top 10 Species in Date Range")
        sorted_species = sorted(
            species_counts.items(), key=lambda x: x[1], reverse=True
        )
        for i, (species, count) in enumerate(sorted_species[:10], 1):
            print(f"  {i:2d}. {species:<55} {count:>8,} obs")

        print_subheader("Top 10 Countries in Date Range")
        sorted_countries = sorted(
            country_counts.items(), key=lambda x: x[1], reverse=True
        )
        for i, (country, count) in enumerate(sorted_countries[:10], 1):
            print(f"  {i:2d}. {country:<5} {count:>10,} observations")


def cmd_top_species(parser, n, show_details=False):
    """Show top N species by observation count."""
    print_header(f"TOP {n} SPECIES")

    top_species = parser.get_top_species(n)

    print()
    print(f"{'Rank':<6} {'Species':<55} {'Observations':>15}")
    print("-" * 80)

    for i, (species, count) in enumerate(top_species, 1):
        print(f"{i:<6} {truncate_text(species, 53):<55} {count:>15,}")

    if show_details and top_species:
        # Show details for top species
        top_species_name = top_species[0][0]
        print_subheader(f"Details for Top Species: {top_species_name}")

        observations = parser.search_by_species(top_species_name)
        country_counts = {}

        for obs in observations:
            country = obs.get("countryCode")
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

        print("\n  Geographic Distribution:")
        sorted_countries = sorted(
            country_counts.items(), key=lambda x: x[1], reverse=True
        )
        for country, count in sorted_countries[:10]:
            pct = (count / len(observations) * 100) if observations else 0
            print(f"    {country:<5} {count:>8,} observations ({pct:.1f}%)")


def cmd_top_countries(parser, n):
    """Show top N countries by observation count."""
    print_header(f"TOP {n} COUNTRIES")

    top_countries = parser.get_top_countries(n)

    print()
    print(f"{'Rank':<6} {'Country':<10} {'Observations':>15}")
    print("-" * 40)

    for i, (country, count) in enumerate(top_countries, 1):
        print(f"{i:<6} {country:<10} {count:>15,}")


def cmd_top_users(parser, n):
    """Show top N users by image count."""
    print_header(f"TOP {n} CONTRIBUTORS")

    top_users = parser.get_top_users(n)

    print()
    print(f"{'Rank':<6} {'User':<55} {'Images':>15}")
    print("-" * 80)

    for i, (user, count) in enumerate(top_users, 1):
        print(f"{i:<6} {truncate_text(user, 53):<55} {count:>15,}")


def cmd_stats(parser):
    """Show detailed statistics."""
    print_header("DETAILED STATISTICS")

    stats = parser.get_statistics()

    print()
    print(f"{'Metric':<45} {'Value':>20}")
    print("-" * 67)
    print(f"{'Total Occurrences':<45} {format_number(stats['total_occurrences']):>20}")
    print(
        f"{'Total Multimedia Records':<45} {format_number(stats['total_multimedia_records']):>20}"
    )
    print(
        f"{'Unique Observations (GBIF IDs)':<45} {format_number(stats['unique_observations']):>20}"
    )
    print(f"{'Unique Species':<45} {format_number(stats['unique_species']):>20}")
    print(f"{'Unique Countries':<45} {format_number(stats['unique_countries']):>20}")
    print(f"{'Unique Contributors':<45} {format_number(stats['unique_users']):>20}")
    print(
        f"{'Average Images per Observation':<45} {stats['avg_images_per_observation']:>20.2f}"
    )
    print(
        f"{'Maximum Images per Observation':<45} {format_number(stats['max_images_per_observation']):>20}"
    )


def main():
    """Main CLI entry point."""
    parser_obj = argparse.ArgumentParser(
        description="Query and analyze GBIF PlantNet observation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --summary
  %(prog)s --species "Acacia dealbata" --limit 20
  %(prog)s --country FR --top-species 10
  %(prog)s --user "john doe" --count
  %(prog)s --observation 2644196009
  %(prog)s --date-range 2019-10-01 2019-10-31
  %(prog)s --top-species 20 --details
  %(prog)s --top-countries 20
  %(prog)s --top-users 20
  %(prog)s --stats
        """,
    )

    # Commands
    parser_obj.add_argument(
        "--summary", action="store_true", help="Display summary of all data"
    )
    parser_obj.add_argument(
        "--species", metavar="NAME", help="Search for observations by species name"
    )
    parser_obj.add_argument(
        "--country",
        metavar="CODE",
        help="Search for observations by country code (e.g., FR, ES)",
    )
    parser_obj.add_argument(
        "--user", metavar="NAME", help="Search for images by user/creator name"
    )
    parser_obj.add_argument(
        "--observation",
        metavar="GBIF_ID",
        help="Show complete details for a specific GBIF ID",
    )
    parser_obj.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Filter observations by date range (YYYY-MM-DD format)",
    )
    parser_obj.add_argument(
        "--top-species",
        type=int,
        metavar="N",
        help="Show top N species by observation count",
    )
    parser_obj.add_argument(
        "--top-countries",
        type=int,
        metavar="N",
        help="Show top N countries by observation count",
    )
    parser_obj.add_argument(
        "--top-users", type=int, metavar="N", help="Show top N users by image count"
    )
    parser_obj.add_argument(
        "--stats", action="store_true", help="Show detailed statistics"
    )

    # Options
    parser_obj.add_argument(
        "--limit", type=int, metavar="N", help="Limit number of results to display"
    )
    parser_obj.add_argument(
        "--count", action="store_true", help="Show counts/summary instead of details"
    )
    parser_obj.add_argument(
        "--details", action="store_true", help="Show additional details"
    )
    parser_obj.add_argument(
        "--show-images", action="store_true", help="Show image information"
    )
    parser_obj.add_argument(
        "--gbif-dir",
        default="./data/raw/gbif",
        help="Path to GBIF directory (default: ./data/raw/gbif)",
    )
    parser_obj.add_argument(
        "--max-rows",
        type=int,
        metavar="N",
        help="Maximum rows to load per file (for testing)",
    )

    args = parser_obj.parse_args()

    # Check if any command was specified
    if not any(
        [
            args.summary,
            args.species,
            args.country,
            args.user,
            args.observation,
            args.date_range,
            args.top_species,
            args.top_countries,
            args.top_users,
            args.stats,
        ]
    ):
        parser_obj.print_help()
        return

    # Initialize parser
    try:
        parser = GBIFParser(gbif_dir=args.gbif_dir)
        print("Loading GBIF data files...")
        print("NOTE: This may take several minutes for large datasets...")
        parser.load_all(max_rows=args.max_rows)
        print("Data loaded successfully!\n")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            f"Make sure you're in the correct directory or specify --gbif-dir",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute commands
    try:
        if args.summary:
            cmd_summary(parser)

        if args.species:
            cmd_species(parser, args.species, args.show_images, args.limit)

        if args.country:
            top_species_count = args.top_species if args.top_species else None
            cmd_country(parser, args.country, top_species_count, args.details)

        if args.user:
            cmd_user(parser, args.user, args.count, args.limit)

        if args.observation:
            cmd_observation(parser, args.observation, not args.count)

        if args.date_range:
            start_date, end_date = args.date_range
            cmd_date_range(parser, start_date, end_date, args.count)

        if args.top_species:
            cmd_top_species(parser, args.top_species, args.details)

        if args.top_countries:
            cmd_top_countries(parser, args.top_countries)

        if args.top_users:
            cmd_top_users(parser, args.top_users)

        if args.stats:
            cmd_stats(parser)

        print()  # Final newline

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
