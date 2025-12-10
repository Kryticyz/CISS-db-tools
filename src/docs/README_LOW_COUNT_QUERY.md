# Low Count Species Query Tool

This tool queries species with low image counts in the cleaned dataset and compares them with GBIF database availability.

## Overview

The `query_low_count_species.py` script finds all species in the PlantNet counts database with image counts below a specified threshold (default: 400), then queries the GBIF database to determine how many images exist for those same species in GBIF. This helps identify:

- **Opportunities**: Species where GBIF has significantly more images than the local dataset
- **Gaps**: Species where GBIF has no images or fewer images than locally available
- **Coverage analysis**: Overall comparison between local and GBIF image availability

## Requirements

- Python 3.7+
- SQLite3 (included with Python)
- Access to both databases:
  - `plantnet_counts.db` - Local image counts database
  - `plantnet_gbif.db` - GBIF observations and multimedia database

## Usage

### Basic Usage

Find species with checked count < 400 (default):

```bash
python3 src/query_low_count_species.py
```

### Custom Threshold

Find species with a different threshold:

```bash
# Find species with count < 500
python3 src/query_low_count_species.py --threshold 500

# Find species with count < 200
python3 src/query_low_count_species.py --threshold 200
```

### Different Datasets

Query different count datasets (original, checked, or unchecked):

```bash
# Query unchecked counts
python3 src/query_low_count_species.py --dataset unchecked

# Query original counts with custom threshold
python3 src/query_low_count_species.py --dataset original --threshold 500
```

### Export to CSV

Export results to a CSV file for further analysis:

```bash
python3 src/query_low_count_species.py --output results.csv

# With custom parameters
python3 src/query_low_count_species.py --threshold 300 --dataset checked --output analysis.csv
```

### Custom Database Paths

Specify custom database locations:

```bash
python3 src/query_low_count_species.py \
    --counts-db /path/to/counts.db \
    --gbif-db /path/to/gbif.db
```

## Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--threshold` | int | 400 | Maximum count threshold (exclusive) |
| `--dataset` | choice | checked | Which dataset to use: `original`, `checked`, or `unchecked` |
| `--counts-db` | path | `./plantnet_counts.db` | Path to counts database |
| `--gbif-db` | path | `./plantnet_gbif.db` | Path to GBIF database |
| `--output`, `-o` | path | None | Export results to CSV file |
| `--help`, `-h` | - | - | Show help message |

## Output Format

### Console Output

The script provides comprehensive console output including:

1. **Progress indicators** - Shows which step is being executed
2. **Results table** - All species sorted by local count (descending)
3. **Summary statistics** - Overall analysis metrics
4. **Top opportunities** - Species with most additional images in GBIF
5. **Species with no GBIF images** - Species where GBIF has zero images

### CSV Output

When using `--output`, the CSV file contains:

| Column | Description |
|--------|-------------|
| `Species` | Species name in `Genus_species` format |
| `{Dataset}_Count` | Local image count from specified dataset |
| `GBIF_Images` | Number of images in GBIF database |
| `Difference` | GBIF count minus local count |
| `Has_GBIF_Images` | "Yes" if GBIF has images, "No" otherwise |

## Example Output

### Console

```
==========================================================================================
                             SPECIES WITH CHECKED COUNT < 400                 
==========================================================================================


[1/3] Querying counts database...
Found 134 species with checked count < 400

[2/3] Querying GBIF database for image counts...

[3/3] Combining results...

RESULTS
-------

Rank   Species                                         Checked Count     GBIF Images      Difference
----------------------------------------------------------------------------------------------------
1      Acacia_floribunda                                         398               0            -398
2      Plantago_coronopus                                        392             792            +400
3      Cylindropuntia_kleiniae                                   386               0            -386
...

SUMMARY STATISTICS
------------------

Total species analyzed: 134
Total local checked images: 32,818
Total GBIF images: 61,747
Net difference: 28,929

Species with more images in GBIF: 27 (20.1%)
Species with same count: 2 (1.5%)
Species with fewer images in GBIF: 105 (78.4%)

Species with GBIF images available: 97 (72.4%)
Species without any GBIF images: 37 (27.6%)

TOP 20 OPPORTUNITIES (Most Additional Images in GBIF)
-----------------------------------------------------

Rank   Species                                            Local       GBIF      Additional
------------------------------------------------------------------------------------------
1      Ligustrum_vulgare                                    361      7,732           7,371
2      Ilex_aquifolium                                      367      6,600           6,233
3      Vicia_sativa                                          82      5,293           5,211
...
```

### CSV

```csv
Species,Checked_Count,GBIF_Images,Difference,Has_GBIF_Images
Acacia_floribunda,398,0,-398,No
Plantago_coronopus,392,792,400,Yes
Cylindropuntia_kleiniae,386,0,-386,No
Oxalis_corniculata,375,1736,1361,Yes
Ilex_aquifolium,367,6600,6233,Yes
```

## Use Cases

### 1. Identify Data Collection Opportunities

Find species where GBIF has many more images than your local dataset:

```bash
python3 src/query_low_count_species.py --threshold 400 --output opportunities.csv
```

Look at the "TOP 20 OPPORTUNITIES" section to prioritize which species to download from GBIF.

### 2. Find Coverage Gaps

Identify species where GBIF has no images:

```bash
python3 src/query_low_count_species.py --threshold 500
```

Check the "SPECIES WITH NO GBIF IMAGES" section. These species may require:
- Alternative data sources
- Field collection
- Verification of scientific name (may be synonyms)

### 3. Dataset Quality Analysis

Compare different cleaning stages:

```bash
# Original dataset
python3 src/query_low_count_species.py --dataset original --threshold 400 -o original_analysis.csv

# Checked dataset
python3 src/query_low_count_species.py --dataset checked --threshold 400 -o checked_analysis.csv

# Unchecked dataset
python3 src/query_low_count_species.py --dataset unchecked --threshold 400 -o unchecked_analysis.csv
```

### 4. Flexible Threshold Analysis

Analyze different threshold levels:

```bash
# Very low count species (< 100)
python3 src/query_low_count_species.py --threshold 100 -o very_low.csv

# Low count species (< 300)
python3 src/query_low_count_species.py --threshold 300 -o low.csv

# Medium-low count species (< 500)
python3 src/query_low_count_species.py --threshold 500 -o medium_low.csv
```

## How It Works

### Step 1: Query Local Counts Database

The script queries the `image_counts` table to find all species where the specified count column (checked_count, unchecked_count, or original_count) is below the threshold:

```sql
SELECT directory, {column}
FROM image_counts
WHERE {column} IS NOT NULL
  AND {column} < ?
ORDER BY {column} DESC, directory ASC
```

### Step 2: Query GBIF Database

For each species found, the script queries the GBIF database by:
1. Joining the `multimedia` table with the `occurrences` table on `gbifID`
2. Filtering for the species using the normalized name
3. Counting distinct image records (type = 'StillImage')

```sql
SELECT COUNT(DISTINCT m.id) as image_count
FROM multimedia m
INNER JOIN occurrences o ON m.gbifID = o.gbifID
WHERE o.species_normalized = ?
  AND m.type = 'StillImage'
```

### Step 3: Combine and Analyze

The script combines the results from both databases and calculates:
- Differences between local and GBIF counts
- Percentage statistics
- Top opportunities for data augmentation
- Species with missing GBIF coverage

## Performance

- **Database queries**: Indexed queries on both databases for fast lookups
- **Typical runtime**: 
  - 134 species: ~2-5 seconds
  - 500 species: ~10-20 seconds
- **Memory usage**: Minimal (< 100 MB for typical datasets)

## Interpretation Guide

### Positive Difference

`GBIF Images > Local Count` → **Opportunity**: GBIF has more images available for download

**Example**: `Ilex_aquifolium` has 367 local images but 6,600 in GBIF (+6,233)

**Action**: Consider downloading additional images from GBIF to improve dataset

### Negative Difference

`GBIF Images < Local Count` → **Good Coverage**: Your local dataset is more complete than GBIF

**Example**: `Acacia_floribunda` has 398 local images but 0 in GBIF (-398)

**Action**: No action needed, or consider uploading to GBIF to help the community

### Zero GBIF Images

`GBIF Images = 0` → **Gap**: No GBIF images available

**Possible reasons**:
- Species name may be a synonym (not the accepted name in GBIF)
- Rare species with limited observations
- Regional species not well-represented in GBIF
- Recently described species

**Action**: Check scientific name validity, consider alternative sources

## Troubleshooting

### Database Not Found

```
Error: Counts database not found: ./plantnet_counts.db
```

**Solution**: Run from the correct directory or specify database paths:
```bash
python3 src/query_low_count_species.py --counts-db /path/to/plantnet_counts.db
```

### No Species Found

```
No species found with checked count < 400
```

**Solution**: 
- Try a higher threshold: `--threshold 500`
- Check a different dataset: `--dataset original`
- Verify database has data: `sqlite3 plantnet_counts.db "SELECT COUNT(*) FROM image_counts"`

### Slow Performance

If queries are slow:
1. Ensure database indexes exist (they should be created automatically)
2. Check database file isn't corrupted
3. Consider rebuilding databases using `parse_counts_db.py` and `parse_gbif_db.py`

### Invalid Species Names

Some species might not match between databases due to:
- Name normalization differences (spaces vs underscores)
- Synonym vs accepted names
- Taxonomic updates

The script uses the `species_normalized` field which converts names to `Genus_species` format.

## Related Tools

- `query_unified_db.py` - Query both databases with more advanced options
- `parse_counts_db.py` - Build/rebuild the counts database
- `parse_gbif_db.py` - Build/rebuild the GBIF database
- `query_counts.py` - Query counts database only
- `query_gbif.py` - Query GBIF database only

## Technical Details

### Species Name Matching

Both databases use normalized species names in the format `Genus_species`:
- Spaces are converted to underscores
- Author names are stripped
- Example: `"Acacia dealbata Link"` → `"Acacia_dealbata"`

### Database Schema

#### Counts Database
```sql
CREATE TABLE image_counts (
    id INTEGER PRIMARY KEY,
    directory TEXT NOT NULL UNIQUE,
    original_count INTEGER,
    checked_count INTEGER,
    unchecked_count INTEGER
);
```

#### GBIF Database
```sql
CREATE TABLE occurrences (
    id INTEGER PRIMARY KEY,
    gbifID TEXT NOT NULL UNIQUE,
    species_normalized TEXT,
    ...
);

CREATE TABLE multimedia (
    id INTEGER PRIMARY KEY,
    gbifID TEXT NOT NULL,
    type TEXT,
    identifier TEXT,
    ...
);
```

## License

This script is part of the PlantNet data mining tools and is provided as-is for educational and research purposes.

## Author

Tynan Matthews
E: tynan@matthews.solutions

---

Last updated: 2024