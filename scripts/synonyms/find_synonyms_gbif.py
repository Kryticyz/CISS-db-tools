#!/usr/bin/env python3
"""
find_synonyms_gbif.py - Query GBIF API directly for scientific plant synonyms

This script reads species names from no_images.txt and uses the GBIF Species API
to find accepted names and synonyms. This is more reliable than using an LLM
since it queries the authoritative GBIF backbone taxonomy directly.

No API key required!

Usage:
    python find_synonyms_gbif.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--limit N]

Examples:
    # Process all species
    python find_synonyms_gbif.py

    # Test with first 5 species
    python find_synonyms_gbif.py --limit 5

    # Resume interrupted processing
    python find_synonyms_gbif.py --resume

GBIF API Documentation:
    https://www.gbif.org/developer/species
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from time import sleep
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("Error: requests package not installed", file=sys.stderr)
    print("Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Configuration
DEFAULT_INPUT = "data/reports/no_images.txt"
DEFAULT_OUTPUT = "data/processed/synonyms/species_synonyms_gbif.json"
RATE_LIMIT_DELAY = 0.5  # GBIF is generous, but let's be nice
GBIF_API_BASE = "https://api.gbif.org/v1"

# Default minimum confidence score to accept a match (0-100)
DEFAULT_MIN_CONFIDENCE = 80


def parse_species_file(filepath: str) -> list[str]:
    """Parse the no_images.txt file and extract species names."""
    species_list = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines, comments, and error messages
            if not line or line.startswith("#"):
                continue

            # Skip obvious non-species entries
            if line in ["ProfileImages - Copy", "System Volume Information"]:
                continue

            # Convert underscore format to proper species name
            species_name = line.replace("_", " ")

            # Clean up subspecies/variety notation
            species_name = re.sub(r"\s+subsp\s+", " subsp. ", species_name)
            species_name = re.sub(r"\s+var\s+", " var. ", species_name)

            # Handle hybrid notation
            species_name = species_name.replace(" x ", " × ")

            species_list.append(species_name)

    return species_list


def gbif_match_species(species_name: str) -> dict | None:
    """
    Use GBIF Species Match API to find the accepted name for a species.

    Returns match data or None if no good match found.
    """
    url = f"{GBIF_API_BASE}/species/match"
    params = {
        "name": species_name,
        "kingdom": "Plantae",  # Restrict to plants
        "verbose": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Check if we got a match
        if data.get("matchType") == "NONE":
            return None

        return data

    except requests.RequestException as e:
        print(f"  Error querying GBIF match API: {e}", file=sys.stderr)
        return None


def gbif_get_synonyms(usage_key: int) -> list[dict]:
    """
    Get all synonyms for a given GBIF usage key.

    Returns list of synonym records.
    """
    url = f"{GBIF_API_BASE}/species/{usage_key}/synonyms"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        return data.get("results", [])

    except requests.RequestException as e:
        print(f"  Error querying GBIF synonyms API: {e}", file=sys.stderr)
        return []


def gbif_get_species_info(usage_key: int) -> dict | None:
    """
    Get full species information for a given GBIF usage key.
    """
    url = f"{GBIF_API_BASE}/species/{usage_key}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        print(f"  Error querying GBIF species API: {e}", file=sys.stderr)
        return None


def query_gbif_for_species(
    species_name: str, min_confidence: int = DEFAULT_MIN_CONFIDENCE
) -> dict:
    """
    Query GBIF for a species name and return structured results.
    """
    result = {
        "query_name": species_name,
        "gbif_accepted_name": None,
        "gbif_taxon_key": None,
        "gbif_accepted_key": None,
        "match_type": None,
        "match_confidence": None,
        "taxonomic_status": None,
        "synonyms": [],
        "confidence": "none",
        "sources": ["GBIF Backbone Taxonomy"],
        "notes": "",
    }

    # Step 1: Match the species name
    match_data = gbif_match_species(species_name)

    if not match_data:
        result["notes"] = "No match found in GBIF"
        return result

    result["match_type"] = match_data.get("matchType")
    result["match_confidence"] = match_data.get("confidence")
    result["taxonomic_status"] = match_data.get("status")
    result["gbif_taxon_key"] = match_data.get("usageKey")

    # Check confidence threshold
    confidence = match_data.get("confidence", 0)
    if confidence < min_confidence:
        result["notes"] = f"Match confidence too low: {confidence}%"
        result["confidence"] = "low"
        return result

    # Determine the accepted key
    # If the matched name is a synonym, use acceptedUsageKey
    # If it's already accepted, use usageKey
    if match_data.get("status") == "SYNONYM":
        accepted_key = match_data.get("acceptedUsageKey")
        result["gbif_accepted_key"] = accepted_key
        result["gbif_accepted_name"] = match_data.get(
            "species"
        )  # The accepted species name
        result["notes"] = (
            f"Input is a synonym. Accepted name: {match_data.get('species')}"
        )
    else:
        accepted_key = match_data.get("usageKey")
        result["gbif_accepted_key"] = accepted_key
        result["gbif_accepted_name"] = match_data.get(
            "canonicalName"
        ) or match_data.get("scientificName")

    # Set confidence based on match quality
    if confidence >= 95:
        result["confidence"] = "high"
    elif confidence >= MIN_CONFIDENCE:
        result["confidence"] = "medium"
    else:
        result["confidence"] = "low"

    # Step 2: Get synonyms if we have an accepted key
    if accepted_key:
        synonyms_data = gbif_get_synonyms(accepted_key)

        # Extract canonical names from synonyms
        synonym_names = []
        for syn in synonyms_data:
            canonical = syn.get("canonicalName")
            if canonical and canonical != result["gbif_accepted_name"]:
                synonym_names.append(canonical)

        # Remove duplicates while preserving order
        seen = set()
        unique_synonyms = []
        for s in synonym_names:
            if s not in seen:
                seen.add(s)
                unique_synonyms.append(s)

        result["synonyms"] = unique_synonyms

        if not result["notes"]:
            result["notes"] = f"Found {len(unique_synonyms)} synonyms in GBIF"

    return result


def save_results(results: dict, filepath: str):
    """Save results to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_existing_results(filepath: str) -> dict:
    """Load existing results if file exists (for resuming)."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"metadata": {}, "species": {}}


def save_csv_results(results: dict, filepath: Path):
    """Save results to CSV file with one row per synonym relationship."""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "original_name",
                "gbif_accepted_name",
                "gbif_accepted_key",
                "gbif_taxon_key",
                "synonym",
                "match_type",
                "match_confidence",
                "taxonomic_status",
                "confidence",
                "notes",
            ]
        )

        for original, data in results.get("species", {}).items():
            accepted = data.get("gbif_accepted_name", "")
            accepted_key = data.get("gbif_accepted_key", "")
            taxon_key = data.get("gbif_taxon_key", "")
            match_type = data.get("match_type", "")
            match_conf = data.get("match_confidence", "")
            tax_status = data.get("taxonomic_status", "")
            confidence = data.get("confidence", "")
            notes = data.get("notes", "")
            synonyms = data.get("synonyms", [])

            if synonyms:
                for synonym in synonyms:
                    writer.writerow(
                        [
                            original,
                            accepted,
                            accepted_key,
                            taxon_key,
                            synonym,
                            match_type,
                            match_conf,
                            tax_status,
                            confidence,
                            notes,
                        ]
                    )
            else:
                writer.writerow(
                    [
                        original,
                        accepted,
                        accepted_key,
                        taxon_key,
                        "",
                        match_type,
                        match_conf,
                        tax_status,
                        confidence,
                        notes,
                    ]
                )


def main():
    parser = argparse.ArgumentParser(
        description="Query GBIF API directly for plant species synonyms"
    )
    parser.add_argument(
        "--input",
        "-i",
        default=DEFAULT_INPUT,
        help=f"Input file with species names (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON file for synonyms (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of species to process (for testing)",
    )
    parser.add_argument(
        "--resume",
        "-r",
        action="store_true",
        help="Resume from existing output file, skipping already processed species",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=DEFAULT_MIN_CONFIDENCE,
        help=f"Minimum GBIF match confidence to accept (0-100, default: {DEFAULT_MIN_CONFIDENCE})",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format: json, csv, or both (default: both)",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=RATE_LIMIT_DELAY,
        help=f"Delay between API calls in seconds (default: {RATE_LIMIT_DELAY})",
    )

    args = parser.parse_args()

    # Store min confidence for use in queries
    min_confidence = args.min_confidence

    # Get script directory for relative paths
    script_dir = Path(__file__).parent.parent
    input_path = script_dir / args.input
    output_path = script_dir / args.output

    # Parse species list
    print(f"Reading species from: {input_path}")
    species_list = parse_species_file(input_path)
    print(f"Found {len(species_list)} species to process")

    if args.limit:
        species_list = species_list[: args.limit]
        print(f"Limited to {args.limit} species")

    # Load existing results if resuming
    if args.resume:
        results = load_existing_results(output_path)
        print(f"Resuming: {len(results.get('species', {}))} species already processed")
    else:
        results = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "source_file": str(args.input),
                "total_species": len(species_list),
                "api": "GBIF Species API",
                "min_confidence": min_confidence,
            },
            "species": {},
        }

    # Process each species
    processed = 0
    skipped = 0
    found_accepted = 0
    found_synonyms = 0

    for i, species in enumerate(species_list, 1):
        # Skip if already processed (resume mode)
        if args.resume and species in results.get("species", {}):
            skipped += 1
            continue

        print(f"[{i}/{len(species_list)}] Querying GBIF: {species}")

        # Query GBIF API
        result = query_gbif_for_species(species, min_confidence)

        # Store result
        results["species"][species] = result

        if result.get("gbif_accepted_name"):
            found_accepted += 1
            print(
                f"  ✓ Accepted: {result['gbif_accepted_name']} (confidence: {result.get('match_confidence', '?')}%)"
            )

            if result.get("synonyms"):
                found_synonyms += 1
                syn_preview = ", ".join(result["synonyms"][:3])
                if len(result["synonyms"]) > 3:
                    syn_preview += f"... (+{len(result['synonyms']) - 3} more)"
                print(f"    Synonyms: {syn_preview}")
        else:
            print(f"  ✗ No match: {result.get('notes', 'Unknown error')}")

        processed += 1

        # Save intermediate results every 10 species
        if processed % 10 == 0:
            save_results(results, output_path)
            print(f"  [Checkpoint saved: {output_path}]")

        # Rate limiting
        sleep(args.delay)

    # Update metadata
    results["metadata"]["completed"] = datetime.now().isoformat()
    results["metadata"]["processed"] = processed
    results["metadata"]["skipped"] = skipped
    results["metadata"]["found_accepted"] = found_accepted
    results["metadata"]["found_synonyms"] = found_synonyms

    # Save final results
    print("\n" + "=" * 60)
    print("COMPLETE")
    print(f"  Processed: {processed} species")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Found accepted names: {found_accepted} species")
    print(f"  Found synonyms for: {found_synonyms} species")

    # Save JSON output
    if args.format in ["json", "both"]:
        save_results(results, output_path)
        print(f"  JSON results saved to: {output_path}")

    # Save CSV output
    if args.format in ["csv", "both"]:
        csv_path = output_path.with_suffix(".csv")
        save_csv_results(results, csv_path)
        print(f"  CSV results saved to: {csv_path}")

    # Generate summary file with just the synonym mappings
    summary_path = output_path.with_suffix(".txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Species Synonyms Summary (GBIF API)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Source: GBIF Backbone Taxonomy\n")
        f.write(
            "# Format: original_name -> gbif_accepted_name [key] | synonym1, synonym2, ...\n\n"
        )

        for original, data in results["species"].items():
            accepted = data.get("gbif_accepted_name")
            accepted_key = data.get("gbif_accepted_key", "")
            synonyms = data.get("synonyms", [])

            if accepted:
                syn_str = ", ".join(synonyms) if synonyms else "none"
                key_str = f" [{accepted_key}]" if accepted_key else ""
                f.write(f"{original} -> {accepted}{key_str} | {syn_str}\n")
            else:
                f.write(f"{original} -> NOT FOUND\n")

    print(f"  Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
