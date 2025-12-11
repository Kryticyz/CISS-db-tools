# Quick Start: Low Count Species Query

Find species with low image counts and check GBIF availability in seconds.

## TL;DR

```bash
# Run with defaults (checked dataset, threshold < 400)
python3 src/query_low_count_species.py

# Export to CSV
python3 src/query_low_count_species.py --output results.csv

# Custom threshold
python3 src/query_low_count_species.py --threshold 500
```

## What This Does

1. **Finds species** with fewer than 400 images in your cleaned dataset
2. **Checks GBIF** to see how many images exist there
3. **Shows opportunities** where GBIF has more images you could download
4. **Identifies gaps** where GBIF has no images

## Quick Examples

### Find Best Download Opportunities
```bash
python3 src/query_low_count_species.py --output opportunities.csv
```
Look at the "TOP 20 OPPORTUNITIES" section for species with most additional GBIF images.

### Different Thresholds
```bash
# Very sparse species (< 100 images)
python3 src/query_low_count_species.py --threshold 100

# Low count species (< 300 images)
python3 src/query_low_count_species.py --threshold 300

# Medium-low count (< 500 images)
python3 src/query_low_count_species.py --threshold 500
```

### Different Datasets
```bash
# Original
python3 src/query_low_count_species.py --dataset original

# Checked (manually verified)
python3 src/query_low_count_species.py --dataset checked

# Unchecked (Processed by volunteers)
python3 src/query_low_count_species.py --dataset unchecked
```

## Understanding the Output

### Console Output Sections

1. **RESULTS** - All species sorted by local count
2. **SUMMARY STATISTICS** - Overall numbers and percentages
3. **TOP 20 OPPORTUNITIES** - Best species to download from GBIF
4. **SPECIES WITH NO GBIF IMAGES** - Coverage gaps

### CSV Output Columns

| Column | Meaning |
|--------|---------|
| Species | Species name (Genus_species) |
| Checked_Count | Your local image count |
| GBIF_Images | Images available in GBIF |
| Difference | GBIF minus local (positive = opportunity) |
| Has_GBIF_Images | Yes/No |

## Common Use Cases

### I want to find species for which I can download more images
```bash
python3 src/query_low_count_species.py --output download_targets.csv
```
Focus on species with positive "Difference" values.


## Help & Documentation

```bash
# Quick help
python3 src/query_low_count_species.py --help

# Full documentation
cat src/README_LOW_COUNT_QUERY.md

# Analysis summary
cat LOW_COUNT_SPECIES_ANALYSIS.md

# SQL queries
cat src/low_count_species_query.sql
```

## Requirements

- Python 3.7+
- SQLite3 (built into Python)
- Databases:
  - `plantnet_counts.db`
  - `plantnet_gbif.db`

## Troubleshooting

**Database not found?**
```bash
# Make sure you're in the right directory
cd /path/to/plantNet
python3 src/query_low_count_species.py
```
Also ensure you have created the databases by running the following commands:
```bash
python3 src/parse_counts_db.py --create
python3 src/parse_gbif_db.py --create
```

**Slow performance?**
- First run may take 5-10 seconds (normal)
- Subsequent runs should be faster
- Check databases exist and aren't corrupted

## Related Tools

- `query_unified_db.py` - More advanced unified queries
- `query_counts.py` - Query counts database only
- `query_gbif.py` - Query GBIF database only

## Author

Tynan Matthews  
E: tynan@matthews.solutions

---

Last updated: December 2025
