#!/usr/bin/env python3
"""
Species Image Count Analysis Report - Version 3
===============================================

DATA PRIORITY (as specified):
1. checked_count   - HIGHEST priority (ready to use, least work)
2. unchecked_count - MEDIUM priority (some work needed)
3. original_count  - LOWEST priority (most work needed)

THRESHOLDS CALCULATED:
- Tier 1: GBIF + checked_count >= 400
- Tier 2: max(GBIF + checked_count, GBIF + unchecked_count) >= 400
- Tier 3: GBIF + original_count >= 400 (fallback, most work)

NOTE: checked and unchecked are DEPENDENT sources (cannot be summed).
Tier 2 uses the better of the two options.

VERIFICATION:
- All calculations are shown with row counts
- Data integrity checks included
- Missing data explicitly flagged
"""

import csv
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def load_species_list(filepath):
    """Load species from species_list.txt"""
    with open(filepath, "r") as f:
        species = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
    return species


def load_synonyms(filepath):
    """Load species synonyms from JSON file"""
    with open(filepath, "r") as f:
        data = json.load(f)
    return data.get("species", {})


def count_url_lines(species_urls_dir):
    """Count lines in each species URL file"""
    url_counts = {}
    for filename in os.listdir(species_urls_dir):
        if filename.endswith("_urls.txt"):
            species_name = filename.replace("_urls.txt", "")
            filepath = os.path.join(species_urls_dir, filename)
            with open(filepath, "r") as f:
                count = sum(1 for line in f if line.strip())
            url_counts[species_name] = count
    return url_counts


def get_db_counts(db_path):
    """Get counts from SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT directory, original_count, checked_count, unchecked_count FROM image_counts"
    )
    rows = cursor.fetchall()
    conn.close()

    counts = {}
    for row in rows:
        directory, original, checked, unchecked = row
        counts[directory] = {
            "original": original or 0,
            "checked": checked or 0,
            "unchecked": unchecked or 0,
        }
    return counts


def normalize_name(name):
    """Normalize species name for matching"""
    normalized = name.replace(" ", "_").replace("-", "_").replace("×", "x")
    normalized = normalized.replace("subsp.", "subsp").replace("var.", "var")
    return normalized.lower()


def find_url_file_match(species_name, url_counts, synonyms):
    """Find matching URL file for a species"""
    normalized = normalize_name(species_name)

    # Direct match
    for url_file_name, count in url_counts.items():
        if normalize_name(url_file_name) == normalized:
            return url_file_name, count

    # Synonym match
    species_with_space = species_name.replace("_", " ")
    if species_with_space in synonyms:
        syn_data = synonyms[species_with_space]
        gbif_name = syn_data.get("gbif_accepted_name", "")
        if gbif_name:
            gbif_normalized = normalize_name(gbif_name)
            for url_file_name, count in url_counts.items():
                if normalize_name(url_file_name) == gbif_normalized:
                    return url_file_name, count

    # Partial match
    for url_file_name, count in url_counts.items():
        url_norm = normalize_name(url_file_name)
        if normalized in url_norm or url_norm in normalized:
            return url_file_name, count

    return None, 0


def find_db_match(species_name, db_counts):
    """Find matching database entry for a species"""
    normalized = normalize_name(species_name)

    for db_name, counts in db_counts.items():
        if normalize_name(db_name) == normalized:
            return counts

    for db_name, counts in db_counts.items():
        db_normalized = normalize_name(db_name)
        if normalized in db_normalized or db_normalized in normalized:
            return counts

    return {"original": 0, "checked": 0, "unchecked": 0}


def main():
    base_dir = Path(__file__).parent
    species_list_path = base_dir / "species_list.txt"
    synonyms_path = base_dir / "species_synonyms_gbif.json"
    species_urls_dir = base_dir / "species_urls"
    db_path = base_dir / "plantnet_counts.db"
    output_csv = base_dir / "species_report_v3.csv"
    output_report = base_dir / "FINAL_REPORT_v3.md"

    # Load data
    print("Loading data...")
    species_list = load_species_list(species_list_path)
    synonyms = load_synonyms(synonyms_path)
    url_counts = count_url_lines(species_urls_dir)
    db_counts = get_db_counts(db_path)

    # Process each species
    results = []
    for species in species_list:
        url_file, gbif_count = find_url_file_match(species, url_counts, synonyms)
        db_data = find_db_match(species, db_counts)

        checked = db_data["checked"]
        unchecked = db_data["unchecked"]
        original = db_data["original"]

        # Tier calculations
        # Note: checked and unchecked are dependent - use max, not sum
        tier1_total = gbif_count + checked
        tier2_total = max(gbif_count + checked, gbif_count + unchecked)
        tier3_total = gbif_count + original

        results.append(
            {
                "species": species,
                "gbif_urls": gbif_count,
                "checked": checked,
                "unchecked": unchecked,
                "original": original,
                "tier1_gbif_checked": tier1_total,
                "tier2_gbif_max": tier2_total,
                "tier3_gbif_original": tier3_total,
                "tier1_meets_400": "yes" if tier1_total >= 400 else "no",
                "tier2_meets_400": "yes" if tier2_total >= 400 else "no",
                "tier3_meets_400": "yes" if tier3_total >= 400 else "no",
            }
        )

    # Write CSV
    print(f"Writing CSV to {output_csv}")
    fieldnames = [
        "species",
        "gbif_urls",
        "checked",
        "unchecked",
        "original",
        "tier1_gbif_checked",
        "tier2_gbif_max",
        "tier3_gbif_original",
        "tier1_meets_400",
        "tier2_meets_400",
        "tier3_meets_400",
    ]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Calculate statistics
    total = len(results)
    tier1_yes = sum(1 for r in results if r["tier1_meets_400"] == "yes")
    tier2_yes = sum(1 for r in results if r["tier2_meets_400"] == "yes")
    tier3_yes = sum(1 for r in results if r["tier3_meets_400"] == "yes")

    # Data quality checks
    has_gbif = sum(1 for r in results if r["gbif_urls"] > 0)
    has_checked = sum(1 for r in results if r["checked"] > 0)
    has_unchecked = sum(1 for r in results if r["unchecked"] > 0)
    has_original = sum(1 for r in results if r["original"] > 0)
    has_no_data = sum(
        1
        for r in results
        if r["gbif_urls"] == 0
        and r["checked"] == 0
        and r["unchecked"] == 0
        and r["original"] == 0
    )

    # Problem species
    tier3_no = [r for r in results if r["tier3_meets_400"] == "no"]
    tier2_no_but_tier3_yes = [
        r
        for r in results
        if r["tier2_meets_400"] == "no" and r["tier3_meets_400"] == "yes"
    ]
    tier1_no_but_tier2_yes = [
        r
        for r in results
        if r["tier1_meets_400"] == "no" and r["tier2_meets_400"] == "yes"
    ]

    close_to_400 = [r for r in results if 350 <= r["tier1_gbif_checked"] < 400]

    # Generate report
    report = []
    report.append("# Species Image Count Analysis Report (v3)")
    report.append("")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Data Priority (as specified)")
    report.append("")
    report.append("| Priority | Field | Description |")
    report.append("|----------|-------|-------------|")
    report.append("| 1 (Highest) | checked_count | Ready to use, least work |")
    report.append("| 2 | unchecked_count | Some work needed |")
    report.append("| 3 (Lowest) | original_count | Most work needed |")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Summary: Species Meeting 400 Threshold")
    report.append("")
    report.append("| Tier | Calculation | Count | Percentage |")
    report.append("|------|-------------|-------|------------|")
    report.append(
        f"| Tier 1 | GBIF + checked | {tier1_yes} / {total} | **{100 * tier1_yes / total:.1f}%** |"
    )
    report.append(
        f"| Tier 2 | max(GBIF+checked, GBIF+unchecked) | {tier2_yes} / {total} | **{100 * tier2_yes / total:.1f}%** |"
    )
    report.append(
        f"| Tier 3 | GBIF + original | {tier3_yes} / {total} | **{100 * tier3_yes / total:.1f}%** |"
    )
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Verification: Data Coverage")
    report.append("")
    report.append("| Data Source | Species with data | Species without |")
    report.append("|-------------|-------------------|-----------------|")
    report.append(f"| GBIF URLs | {has_gbif} | {total - has_gbif} |")
    report.append(f"| checked_count | {has_checked} | {total - has_checked} |")
    report.append(f"| unchecked_count | {has_unchecked} | {total - has_unchecked} |")
    report.append(f"| original_count | {has_original} | {total - has_original} |")
    report.append(f"| **No data at all** | - | **{has_no_data}** |")
    report.append("")
    report.append("### Limitations / Missing Information")
    report.append("")
    report.append(
        f"- {total - has_gbif} species have no GBIF URL file match (may need synonym lookup)"
    )
    report.append(
        f"- {total - has_checked} species have no checked_count (not yet processed)"
    )
    report.append(f"- {total - has_unchecked} species have no unchecked_count")
    report.append(f"- {has_no_data} species have zero data from all sources")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Problem Species Analysis")
    report.append("")
    report.append(
        f"### Cannot reach 400 even with GBIF + original ({len(tier3_no)} species)"
    )
    report.append("")
    if tier3_no:
        report.append(
            "| Species | GBIF | Checked | Unchecked | Original | Max Total | Shortfall |"
        )
        report.append(
            "|---------|------|---------|-----------|----------|-----------|-----------|"
        )
        for r in sorted(tier3_no, key=lambda x: x["tier3_gbif_original"], reverse=True):
            shortfall = 400 - r["tier3_gbif_original"]
            report.append(
                f"| {r['species']} | {r['gbif_urls']} | {r['checked']} | {r['unchecked']} | {r['original']} | {r['tier3_gbif_original']} | {shortfall} |"
            )
    else:
        report.append("None - all species can reach 400 with original data.")
    report.append("")

    report.append(
        f"### Close to 400 threshold (350-399 in Tier 1): {len(close_to_400)} species"
    )
    report.append("")
    report.append("These are quick wins - need fewer than 50 additional images:")
    report.append("")
    if close_to_400:
        report.append("| Species | GBIF | Checked | Tier 1 Total | Shortfall |")
        report.append("|---------|------|---------|--------------|-----------|")
        for r in sorted(
            close_to_400, key=lambda x: x["tier1_gbif_checked"], reverse=True
        ):
            shortfall = 400 - r["tier1_gbif_checked"]
            report.append(
                f"| {r['species']} | {r['gbif_urls']} | {r['checked']} | {r['tier1_gbif_checked']} | {shortfall} |"
            )
    report.append("")

    report.append(
        f"### Need unchecked processing (Tier 1 < 400, Tier 2 >= 400): {len(tier1_no_but_tier2_yes)} species"
    )
    report.append("")
    report.append("These species can reach 400 by processing unchecked images:")
    report.append("")
    if tier1_no_but_tier2_yes[:20]:
        report.append("| Species | GBIF | Checked | Unchecked | Tier 1 | Tier 2 |")
        report.append("|---------|------|---------|-----------|--------|--------|")
        for r in sorted(
            tier1_no_but_tier2_yes,
            key=lambda x: x["tier2_gbif_max"],
            reverse=True,
        )[:20]:
            report.append(
                f"| {r['species']} | {r['gbif_urls']} | {r['checked']} | {r['unchecked']} | {r['tier1_gbif_checked']} | {r['tier2_gbif_max']} |"
            )
        if len(tier1_no_but_tier2_yes) > 20:
            report.append(
                f"| ... and {len(tier1_no_but_tier2_yes) - 20} more | | | | | |"
            )
    report.append("")

    report.append(
        f"### Need original processing (Tier 2 < 400, Tier 3 >= 400): {len(tier2_no_but_tier3_yes)} species"
    )
    report.append("")
    report.append("These species require processing original (raw) images:")
    report.append("")
    if tier2_no_but_tier3_yes[:20]:
        report.append(
            "| Species | GBIF | Checked | Unchecked | Original | Tier 2 | Tier 3 |"
        )
        report.append(
            "|---------|------|---------|-----------|----------|--------|--------|"
        )
        for r in sorted(
            tier2_no_but_tier3_yes, key=lambda x: x["tier3_gbif_original"], reverse=True
        )[:20]:
            report.append(
                f"| {r['species']} | {r['gbif_urls']} | {r['checked']} | {r['unchecked']} | {r['original']} | {r['tier2_gbif_max']} | {r['tier3_gbif_original']} |"
            )
        if len(tier2_no_but_tier3_yes) > 20:
            report.append(
                f"| ... and {len(tier2_no_but_tier3_yes) - 20} more | | | | | | |"
            )
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Verification: How to check this report")
    report.append("")
    report.append("```sql")
    report.append(
        "-- Verify Tier 1 count (GBIF URLs must be added separately from species_urls/)"
    )
    report.append("SELECT COUNT(*) FROM image_counts WHERE checked_count >= 400;")
    report.append("")
    report.append("-- Verify species with checked data")
    report.append("SELECT COUNT(*) FROM image_counts WHERE checked_count > 0;")
    report.append("")
    report.append("-- Verify species with unchecked data")
    report.append("SELECT COUNT(*) FROM image_counts WHERE unchecked_count > 0;")
    report.append("```")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Data Source Files")
    report.append("")
    report.append(f"- species_list.txt: {len(species_list)} species")
    report.append(f"- species_urls/: {len(url_counts)} URL files")
    report.append(f"- plantnet_counts.db: {len(db_counts)} entries")
    report.append(f"- species_synonyms_gbif.json: {len(synonyms)} synonym entries")
    report.append("")

    # Write report
    print(f"Writing report to {output_report}")
    with open(output_report, "w") as f:
        f.write("\n".join(report))

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total species: {total}")
    print(f"")
    print(
        f"Tier 1 (GBIF + checked >= 400):           {tier1_yes:4d} ({100 * tier1_yes / total:5.1f}%)"
    )
    print(
        f"Tier 2 (max(GBIF+checked, GBIF+unchecked) >= 400): {tier2_yes:4d} ({100 * tier2_yes / total:5.1f}%)"
    )
    print(
        f"Tier 3 (GBIF + original >= 400):          {tier3_yes:4d} ({100 * tier3_yes / total:5.1f}%)"
    )
    print(f"")
    print(f"Cannot reach 400: {len(tier3_no)} species")
    print(f"Close to 400 (350-399): {len(close_to_400)} species")
    print("=" * 60)


if __name__ == "__main__":
    main()
