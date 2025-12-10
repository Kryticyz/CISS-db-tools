#!/usr/bin/env python3
"""
Script to fetch GBIF image URLs for a given plant species.
Prefers images from Australia (country code AU).
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def normalize_species_name(name):
    """
    Normalize species name to match database format.
    Strips author names and converts to Genus_species format.

    Examples:
        "Acacia dealbata Link" -> "Acacia_dealbata"
        "Mercurialis annua L." -> "Mercurialis_annua"
        "Acacia dealbata" -> "Acacia_dealbata"
    """
    # Remove common author abbreviations and anything after them
    author_markers = [" L.", " Link", " DC.", " Mill.", " Sw.", " ("]
    for marker in author_markers:
        if marker in name:
            name = name.split(marker)[0]

    # Take only first two words (genus and species)
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    elif len(parts) == 1:
        return parts[0]
    return name


def get_species_urls(
    species_name, db_path="./plantnet_gbif.db", limit=400, prefer_country="AU"
):
    """
    Fetch image URLs for a given species from GBIF database.

    Args:
        species_name: Scientific name of the species (e.g., "Acacia dealbata")
        db_path: Path to the GBIF SQLite database
        limit: Maximum number of URLs to return (default: 400)
        prefer_country: Country code to prioritize (default: 'AU' for Australia)

    Returns:
        List of image URL dictionaries with metadata
    """
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            f"Please run 'python src/parse_gbif_db.py --create' first."
        )

    # Normalize species name
    normalized_name = normalize_species_name(species_name)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if species exists
    cursor.execute(
        """
        SELECT COUNT(DISTINCT gbifID) as count
        FROM occurrences
        WHERE species_normalized = ?
           OR acceptedScientificName_normalized = ?
    """,
        (normalized_name, normalized_name),
    )

    result = cursor.fetchone()
    if result["count"] == 0:
        conn.close()
        raise ValueError(
            f"Species '{species_name}' (normalized: '{normalized_name}') not found in database"
        )

    # Fetch URLs with preference for specified country
    # Strategy: Get preferred country first, then fill remaining with others
    urls = []

    # First, get images from preferred country
    cursor.execute(
        """
        SELECT DISTINCT
            m.identifier as url,
            m.gbifID,
            o.countryCode,
            o.species_normalized,
            o.scientificName,
            m.creator,
            m.license,
            m.title,
            m.created
        FROM multimedia m
        INNER JOIN occurrences o ON m.gbifID = o.gbifID
        WHERE (o.species_normalized = ? OR o.acceptedScientificName_normalized = ?)
          AND m.identifier IS NOT NULL
          AND m.identifier != ''
          AND o.countryCode = ?
        ORDER BY m.created DESC
        LIMIT ?
    """,
        (normalized_name, normalized_name, prefer_country, limit),
    )

    for row in cursor.fetchall():
        urls.append(
            {
                "url": row["url"],
                "gbifID": row["gbifID"],
                "countryCode": row["countryCode"],
                "species": row["species_normalized"],
                "scientificName": row["scientificName"],
                "creator": row["creator"],
                "license": row["license"],
                "title": row["title"],
                "created": row["created"],
            }
        )

    # If we haven't reached the limit, get images from other countries
    remaining = limit - len(urls)
    if remaining > 0:
        cursor.execute(
            """
            SELECT DISTINCT
                m.identifier as url,
                m.gbifID,
                o.countryCode,
                o.species_normalized,
                o.scientificName,
                m.creator,
                m.license,
                m.title,
                m.created
            FROM multimedia m
            INNER JOIN occurrences o ON m.gbifID = o.gbifID
            WHERE (o.species_normalized = ? OR o.acceptedScientificName_normalized = ?)
              AND m.identifier IS NOT NULL
              AND m.identifier != ''
              AND (o.countryCode != ? OR o.countryCode IS NULL)
            ORDER BY m.created DESC
            LIMIT ?
        """,
            (normalized_name, normalized_name, prefer_country, remaining),
        )

        for row in cursor.fetchall():
            urls.append(
                {
                    "url": row["url"],
                    "gbifID": row["gbifID"],
                    "countryCode": row["countryCode"],
                    "species": row["species_normalized"],
                    "scientificName": row["scientificName"],
                    "creator": row["creator"],
                    "license": row["license"],
                    "title": row["title"],
                    "created": row["created"],
                }
            )

    conn.close()
    return urls


def print_summary(species_name, urls, prefer_country):
    """Print a summary of the fetched URLs."""
    print(f"\n{'=' * 70}")
    print(f"Species: {species_name}")
    print(f"{'=' * 70}")
    print(f"Total URLs found: {len(urls)}")

    # Count by country
    country_counts = {}
    for url_info in urls:
        country = url_info["countryCode"] or "Unknown"
        country_counts[country] = country_counts.get(country, 0) + 1

    print(f"\nImages by country:")
    for country, count in sorted(
        country_counts.items(), key=lambda x: x[1], reverse=True
    ):
        marker = " (preferred)" if country == prefer_country else ""
        print(f"  {country}: {count}{marker}")

    print(f"\n{'=' * 70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GBIF image URLs for a plant species, preferring images from a specific country.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get 400 URLs for Acacia dealbata, preferring Australian images
  python src/get_species_urls.py "Acacia dealbata"

  # Get 200 URLs
  python src/get_species_urls.py "Acacia dealbata" --limit 200

  # Prefer images from France instead of Australia
  python src/get_species_urls.py "Quercus robur" --country FR

  # Output only URLs (no metadata)
  python src/get_species_urls.py "Acacia dealbata" --urls-only

  # Save to file
  python src/get_species_urls.py "Acacia dealbata" --output urls.txt
        """,
    )

    parser.add_argument("species", help='Species name (e.g., "Acacia dealbata")')
    parser.add_argument(
        "--limit",
        type=int,
        default=400,
        help="Maximum number of URLs to fetch (default: 400)",
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
        "--urls-only",
        action="store_true",
        help="Output only URLs, no metadata or summary",
    )
    parser.add_argument(
        "--output", "-o", help="Output file path (default: print to stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["simple", "detailed", "json"],
        default="simple",
        help="Output format (default: simple)",
    )

    args = parser.parse_args()

    try:
        # Fetch URLs
        urls = get_species_urls(
            args.species,
            db_path=args.db_path,
            limit=args.limit,
            prefer_country=args.country,
        )

        if not urls:
            print(f"No images found for species '{args.species}'", file=sys.stderr)
            sys.exit(1)

        # Prepare output
        output_lines = []

        if args.urls_only:
            # Just URLs
            for url_info in urls:
                output_lines.append(url_info["url"])
        elif args.format == "json":
            # JSON format
            import json

            output_lines.append(json.dumps(urls, indent=2))
        elif args.format == "detailed":
            # Detailed format with metadata
            for i, url_info in enumerate(urls, 1):
                output_lines.append(f"{i}. {url_info['url']}")
                output_lines.append(
                    f"   Country: {url_info['countryCode'] or 'Unknown'}"
                )
                output_lines.append(f"   GBIF ID: {url_info['gbifID']}")
                output_lines.append(f"   Creator: {url_info['creator'] or 'Unknown'}")
                output_lines.append(f"   License: {url_info['license'] or 'Unknown'}")
                output_lines.append("")
        else:
            # Simple format (default)
            for url_info in urls:
                output_lines.append(url_info["url"])

        # Output to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write("\n".join(output_lines))

            if not args.urls_only:
                print_summary(args.species, urls, args.country)
                print(f"URLs saved to: {output_path}")
        else:
            # Print summary first if not urls-only
            if not args.urls_only and args.format != "json":
                print_summary(args.species, urls, args.country)

            # Print URLs/data
            print("\n".join(output_lines))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
