#!/usr/bin/env python3
"""
find_synonyms.py - Query Anthropic Claude API for scientific plant synonyms

This script reads species names from no_images.txt and uses Claude with web search
to find scientific synonyms. Only high-confidence synonyms are stored.

Requirements:
    pip install anthropic

Environment:
    ANTHROPIC_API_KEY - Your Anthropic API key

Usage:
    python find_synonyms.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--limit N]

Examples:
    # Process all species
    python find_synonyms.py

    # Test with first 5 species
    python find_synonyms.py --limit 5

    # Resume interrupted processing
    python find_synonyms.py --resume

    # Export to CSV format
    python find_synonyms.py --format csv
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

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed", file=sys.stderr)
    print("Install with: pip install anthropic", file=sys.stderr)
    sys.exit(1)

# Configuration
DEFAULT_INPUT = "no_images.txt"
DEFAULT_OUTPUT = "species_synonyms.json"
RATE_LIMIT_DELAY = 60.0  # Seconds between API calls to avoid rate limiting

SYSTEM_PROMPT = """You are a botanical taxonomist expert with comprehensive knowledge of plant nomenclature, taxonomic databases, and scientific naming conventions.

Your PRIMARY GOAL is to find the name that GBIF (Global Biodiversity Information Facility) uses for a given plant species. The user has species names that were not found in GBIF, and needs to find the GBIF-accepted name or the most commonly used synonym in GBIF's database.

CRITICAL PRIORITY - GBIF FIRST:
1. ALWAYS search GBIF.org FIRST (https://www.gbif.org/species/search)
2. Look for the "accepted name" that GBIF uses for this species
3. Check what synonyms GBIF lists and which name has the most occurrence records
4. The goal is to find a name that will return results when querying GBIF's database

Your task is to find the GBIF-ACCEPTED NAME or MOST COMMON SYNONYM for plant species. Focus on:
- The name GBIF considers "accepted"
- Synonyms that have occurrence records in GBIF
- The most commonly used name in biodiversity databases

SEARCH PRIORITY (in order):
1. GBIF (Global Biodiversity Information Facility) - gbif.org - HIGHEST PRIORITY
2. GBIF Backbone Taxonomy
3. POWO (Plants of the World Online - Kew) - secondary verification
4. World Flora Online - secondary verification

CRITICAL GUIDELINES:
1. Search GBIF FIRST for every species query
2. Report the GBIF-accepted name as the primary result
3. List synonyms in order of their usage frequency in GBIF (most records first)
4. ONLY return synonyms you can verify exist in GBIF with HIGH CONFIDENCE
5. Each synonym must be a proper scientific name (Genus species or Genus species var./subsp.)
6. DO NOT include:
   - Common names
   - Names that don't appear in GBIF
   - Your own guesses or interpolations

7. If the input is only a genus name (no species epithet), find the accepted genus name in GBIF

8. For subspecies/varieties, check if GBIF uses the full subspecific name or just the species name

Return your response as a JSON object with this exact structure:
{
    "query_name": "the original species name queried",
    "gbif_accepted_name": "the name GBIF lists as accepted (this is the PRIMARY result)",
    "gbif_taxon_key": "GBIF taxon key/ID if found (e.g., '2874951')",
    "synonyms": ["list", "of", "synonyms", "found", "in", "GBIF", "ordered", "by", "usage"],
    "confidence": "high" or "medium" or "low",
    "sources": ["GBIF", "and any other sources consulted"],
    "notes": "any relevant notes, especially about GBIF record counts or naming discrepancies"
}

If you cannot find the species in GBIF, return:
{
    "query_name": "the original species name",
    "gbif_accepted_name": null,
    "gbif_taxon_key": null,
    "synonyms": [],
    "confidence": "none",
    "sources": ["GBIF"],
    "notes": "Species not found in GBIF. Explanation of search attempts."
}"""


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


def query_synonyms(client: anthropic.Anthropic, species_name: str) -> dict:
    """Query Claude API with web search for species synonyms."""

    user_message = f"""Find the GBIF-accepted name and synonyms for the plant species: **{species_name}**

IMPORTANT: Search GBIF.org FIRST and PRIORITIZE GBIF results.

Please:
1. Search https://www.gbif.org/species/search for this species name
2. Find what name GBIF considers "accepted" for this taxon
3. List any synonyms that appear in GBIF's taxonomy
4. Note the GBIF taxon key/ID if you find it
5. Report which name has the most occurrence records in GBIF

The goal is to find a name that will successfully return results when querying the GBIF database."""

    try:
        # Use Claude with web search tool
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=[
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
            ],
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Extract the text response
        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        # Try to parse JSON from the response
        json_match = re.search(r"\{[\s\S]*\}", result_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                result["query_name"] = species_name  # Ensure original name is preserved
                # Normalize field name for backward compatibility
                if "gbif_accepted_name" in result and "accepted_name" not in result:
                    result["accepted_name"] = result["gbif_accepted_name"]
                return result
            except json.JSONDecodeError:
                pass

        # If JSON parsing fails, return a structured error response
        return {
            "query_name": species_name,
            "gbif_accepted_name": None,
            "accepted_name": None,
            "gbif_taxon_key": None,
            "synonyms": [],
            "confidence": "none",
            "sources": [],
            "notes": f"Could not parse response: {result_text[:500]}",
        }

    except anthropic.APIError as e:
        print(f"  API Error for {species_name}: {e}", file=sys.stderr)
        return {
            "query_name": species_name,
            "gbif_accepted_name": None,
            "accepted_name": None,
            "gbif_taxon_key": None,
            "synonyms": [],
            "confidence": "none",
            "sources": [],
            "notes": f"API error: {str(e)}",
        }


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


def main():
    parser = argparse.ArgumentParser(
        description="Query Anthropic Claude API for plant species synonyms"
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
        "--high-confidence-only",
        action="store_true",
        default=True,
        help="Only save high confidence synonyms (default: True)",
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

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'", file=sys.stderr)
        sys.exit(1)

    # Initialize client
    client = anthropic.Anthropic()

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
            },
            "species": {},
        }

    # Process each species
    processed = 0
    skipped = 0
    found_synonyms = 0

    for i, species in enumerate(species_list, 1):
        # Skip if already processed (resume mode)
        if args.resume and species in results.get("species", {}):
            skipped += 1
            continue

        print(f"[{i}/{len(species_list)}] Querying: {species}")

        # Query API
        result = query_synonyms(client, species)

        # Filter by confidence if requested
        if args.high_confidence_only and result.get("confidence") not in [
            "high",
            "medium",
        ]:
            print(f"  Skipped (low confidence): {result.get('notes', 'No notes')[:80]}")
        else:
            # Store result
            results["species"][species] = result

            if result.get("synonyms"):
                found_synonyms += 1
                print(
                    f"  Found {len(result['synonyms'])} synonyms: {', '.join(result['synonyms'][:3])}..."
                )
                if result.get("accepted_name"):
                    print(f"  Accepted name: {result['accepted_name']}")
            else:
                print(f"  No synonyms found")

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
    results["metadata"]["found_synonyms"] = found_synonyms

    # Save final results
    print("\n" + "=" * 60)
    print(f"COMPLETE")
    print(f"  Processed: {processed} species")
    print(f"  Skipped (already done): {skipped}")
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
        f.write(f"# Species Synonyms Summary (GBIF-focused)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(
            f"# Format: original_name -> gbif_accepted_name [taxon_key] | synonym1, synonym2, ...\n\n"
        )

        for original, data in results["species"].items():
            accepted = data.get("gbif_accepted_name") or data.get(
                "accepted_name", "Unknown"
            )
            taxon_key = data.get("gbif_taxon_key", "")
            synonyms = data.get("synonyms", [])
            if accepted or synonyms:
                syn_str = ", ".join(synonyms) if synonyms else "none"
                key_str = f" [{taxon_key}]" if taxon_key else ""
                f.write(f"{original} -> {accepted}{key_str} | {syn_str}\n")

    print(f"  Summary saved to: {summary_path}")


def save_csv_results(results: dict, filepath: Path):
    """Save results to CSV file with one row per synonym relationship."""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "original_name",
                "gbif_accepted_name",
                "gbif_taxon_key",
                "synonym",
                "confidence",
                "sources",
                "notes",
            ]
        )

        for original, data in results.get("species", {}).items():
            accepted = data.get("gbif_accepted_name") or data.get("accepted_name", "")
            taxon_key = data.get("gbif_taxon_key", "")
            confidence = data.get("confidence", "")
            sources = "; ".join(data.get("sources", []))
            notes = data.get("notes", "")
            synonyms = data.get("synonyms", [])

            if synonyms:
                for synonym in synonyms:
                    writer.writerow(
                        [
                            original,
                            accepted,
                            taxon_key,
                            synonym,
                            confidence,
                            sources,
                            notes,
                        ]
                    )
            else:
                # Still write a row even if no synonyms found
                writer.writerow(
                    [original, accepted, taxon_key, "", confidence, sources, notes]
                )


if __name__ == "__main__":
    main()
