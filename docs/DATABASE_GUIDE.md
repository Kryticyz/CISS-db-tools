# PlantNet Database Tools - SQLite Edition

This directory contains scripts for building and querying SQLite databases from PlantNet GBIF and image count data. The database approach provides **significantly faster** queries and enables powerful **cross-database joins** and aggregations.

## Overview

The database tools consist of three main components:

1. **`parse_gbif_db.py`** - Builds SQLite database from GBIF multimedia.txt and occurrence.txt
2. **`parse_counts_db.py`** - Builds SQLite database from image count CSV files
3. **`query_unified_db.py`** - Unified query tool that joins and analyzes both databases

### Species Name Normalization

Both databases use **underscore-separated species names** (e.g., `Acacia_dealbata`) to match filesystem directory naming conventions. This enables seamless joining between:
- GBIF observations (scientific names)
- Image directories (filesystem names)

Author names are automatically stripped:
- `"Acacia dealbata Link"` → `Acacia_dealbata`
- `"Mercurialis annua L."` → `Mercurialis_annua`

## Quick Start

### Step 1: Create Databases

```bash
# Create GBIF database (2-5 minutes for full dataset)
python scripts/data_processing/parse_gbif_db.py --create
# Or use CLI: plantnet-db-build --create

# Or test with subset (5 seconds)
python scripts/data_processing/parse_gbif_db.py --create --max-rows 10000

# Create counts database (< 1 second)
python scripts/data_processing/parse_counts_db.py --create
```

### Step 2: Verify Databases

```bash
# Check GBIF database
python scripts/data_processing/parse_gbif_db.py --info

# Check counts database
python scripts/data_processing/parse_counts_db.py --info
```

### Step 3: Query Data

```bash
# Summary of both databases
python scripts/database/query_unified_db.py --summary
# Or use CLI: plantnet-db-query --summary

# Search for species in both databases
python scripts/database/query_unified_db.py --species "Acacia_dealbata"
# Or use CLI: plantnet-db-query --species "Acacia_dealbata"

# Compare coverage
python scripts/database/query_unified_db.py --compare-coverage

# Top species by combined metric
python scripts/database/query_unified_db.py --top-combined 20
```

## Database Schemas

### GBIF Database (`plantnet_gbif.db`)

#### `multimedia` Table
Stores image metadata linked to observations.

```sql
CREATE TABLE multimedia (
    id INTEGER PRIMARY KEY,
    gbifID TEXT NOT NULL,           -- Links to occurrences
    type TEXT,                      -- Usually "StillImage"
    format TEXT,                    -- e.g., "image/jpeg"
    identifier TEXT,                -- Image URL
    reference_url TEXT,             -- Source URL
    title TEXT,                     -- e.g., "Acacia: flower"
    description TEXT,
    creator TEXT,                   -- Photographer username
    created TEXT,                   -- Timestamp
    license TEXT
);
```

**Indexes:** `gbifID`, `creator`

#### `occurrences` Table
Stores plant observation records.

```sql
CREATE TABLE occurrences (
    id INTEGER PRIMARY KEY,
    gbifID TEXT NOT NULL UNIQUE,
    scientificName TEXT,                     -- Original name with author
    species_normalized TEXT,                 -- Genus_species format
    acceptedScientificName TEXT,
    acceptedScientificName_normalized TEXT,  -- Also normalized
    kingdom TEXT,
    phylum TEXT,
    class TEXT,
    orderName TEXT,
    family TEXT,
    genus TEXT,
    species TEXT,
    countryCode TEXT,                        -- ISO code (FR, ES, etc.)
    stateProvince TEXT,
    locality TEXT,
    decimalLatitude REAL,
    decimalLongitude REAL,
    coordinateUncertaintyInMeters REAL,
    elevation REAL,
    eventDate TEXT,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    recordedBy TEXT,                         -- Observer name
    individualCount INTEGER,
    basisOfRecord TEXT,
    occurrenceStatus TEXT,
    license TEXT,
    reference_url TEXT,
    issue TEXT,
    mediaType TEXT
);
```

**Indexes:** `gbifID`, `scientificName`, `species_normalized`, `acceptedScientificName_normalized`, `countryCode`, `family`, `genus`, `year`

### Counts Database (`plantnet_counts.db`)

#### `image_counts` Table
Stores image counts for each species directory.

```sql
CREATE TABLE image_counts (
    id INTEGER PRIMARY KEY,
    directory TEXT NOT NULL UNIQUE,  -- Species name (Genus_species)
    original_count INTEGER,          -- Before cleaning
    checked_count INTEGER,           -- After manual checking
    unchecked_count INTEGER          -- After automated cleaning
);
```

**Indexes:** `directory`, `original_count`, `checked_count`, `unchecked_count`

## Command Reference

### parse_gbif_db.py

Build GBIF SQLite database from text files.

```bash
# Create database with all data
python src/parse_gbif_db.py --create

# Create with subset (for testing)
python src/parse_gbif_db.py --create --max-rows 10000

# Show database info
python src/parse_gbif_db.py --info

# Custom paths
python src/parse_gbif_db.py --create \
    --db-path ./my_gbif.db \
    --gbif-dir ./data/plantnet_gbif
```

**Options:**
- `--create` - Build database from source files
- `--info` - Display database statistics
- `--db-path PATH` - Database output path (default: `./plantnet_gbif.db`)
- `--gbif-dir PATH` - Source data directory (default: `./plantnet_gbif`)
- `--max-rows N` - Limit rows per file for testing

### parse_counts_db.py

Build counts SQLite database from CSV files.

```bash
# Create database
python src/parse_counts_db.py --create

# Show database info
python src/parse_counts_db.py --info

# Custom paths
python src/parse_counts_db.py --create \
    --db-path ./my_counts.db \
    --counts-dir ./data/counts
```

**Options:**
- `--create` - Build database from CSV files
- `--info` - Display database statistics
- `--db-path PATH` - Database output path (default: `./plantnet_counts.db`)
- `--counts-dir PATH` - Source CSV directory (default: `./counts`)

### query_unified_db.py

Query both databases with SQL-powered joins and aggregations.

```bash
# Summary of both databases
python src/query_unified_db.py --summary

# Search for species
python src/query_unified_db.py --species "Acacia_dealbata" --details

# Compare coverage between databases
python src/query_unified_db.py --compare-coverage --limit 50

# Top species by combined metric (observations + images)
python src/query_unified_db.py --top-combined 30 --dataset checked

# Species in a specific country with image counts
python src/query_unified_db.py --country FR --limit 50

# Family statistics
python src/query_unified_db.py --family Fabaceae

# Search directories by pattern
python src/query_unified_db.py --search "Acacia"
```

**Commands:**
- `--summary` - Display summary of both databases
- `--species NAME` - Search for species in both databases
- `--compare-coverage` - Compare coverage between databases
- `--top-combined N` - Show top N species by combined metric
- `--country CODE` - Show species in country with image counts
- `--family NAME` - Show statistics for a plant family
- `--search PATTERN` - Search directories by pattern

**Options:**
- `--details` - Show additional details
- `--limit N` - Limit number of results (default: 50)
- `--dataset {original|checked|unchecked}` - Which count dataset to use (default: checked)
- `--gbif-db PATH` - Path to GBIF database
- `--counts-db PATH` - Path to counts database

## Usage Examples

### Example 1: Complete Workflow

```bash
# 1. Build both databases
python src/parse_gbif_db.py --create
python src/parse_counts_db.py --create

# 2. Get overview
python src/query_unified_db.py --summary

# 3. Find species with both observations and images
python src/query_unified_db.py --compare-coverage --limit 20

# 4. Search specific species
python src/query_unified_db.py --species "Quercus_robur" --details
```

### Example 2: Species Research

```bash
# Search for all Acacia species
python src/query_unified_db.py --search "Acacia"

# Get details on specific species
python src/query_unified_db.py --species "Acacia_dealbata" --details

# Output:
# GBIF Observations: 150 observations in 8 countries
# Image Counts: 634 checked images, 667 unchecked
```

### Example 3: Geographic Analysis

```bash
# Species observed in France
python src/query_unified_db.py --country FR --limit 50

# Shows which species have image directories
# Rank   Species                  Observations     Images  Has Images
# 1      Plantago_lanceolata            15           644    ✓
# 2      Taraxacum_officinale           12             0    ✗
```

### Example 4: Family-Level Analysis

```bash
# Analyze Fabaceae (legume) family
python src/query_unified_db.py --family Fabaceae

# Output:
# GBIF Data:
#   Unique species: 45
#   Total observations: 234
# Image Counts:
#   Species with images: 38
#   Total images: 12,450
```

### Example 5: Coverage Comparison

```bash
# Find gaps in coverage
python src/query_unified_db.py --compare-coverage

# Shows:
# - Species in both databases (can be linked)
# - Species only in GBIF (need images)
# - Species only in counts (need observations)
```

## Advanced Usage

### Direct SQL Queries

You can use any SQLite client to query the databases directly:

```bash
# Using sqlite3 command-line tool
sqlite3 plantnet_gbif.db

# Example queries:
sqlite> SELECT COUNT(*) FROM occurrences WHERE countryCode = 'FR';
sqlite> SELECT species_normalized, COUNT(*) 
        FROM occurrences 
        GROUP BY species_normalized 
        ORDER BY COUNT(*) DESC 
        LIMIT 10;
```

### Python API

```python
import sqlite3

# Connect to databases
gbif_conn = sqlite3.connect('./plantnet_gbif.db')
counts_conn = sqlite3.connect('./plantnet_counts.db')

# Query GBIF
cursor = gbif_conn.cursor()
cursor.execute("""
    SELECT species_normalized, COUNT(*) 
    FROM occurrences 
    WHERE countryCode = 'FR' 
    GROUP BY species_normalized
""")
species_counts = cursor.fetchall()

# Query counts
cursor = counts_conn.cursor()
cursor.execute("""
    SELECT directory, checked_count 
    FROM image_counts 
    WHERE checked_count > 500
    ORDER BY checked_count DESC
""")
high_count_dirs = cursor.fetchall()

# Join data (manual)
for species, count in species_counts:
    cursor = counts_conn.cursor()
    cursor.execute(
        "SELECT checked_count FROM image_counts WHERE directory = ?",
        (species,)
    )
    result = cursor.fetchone()
    img_count = result[0] if result else 0
    print(f"{species}: {count} obs, {img_count} images")

gbif_conn.close()
counts_conn.close()
```

### Attach Databases for SQL Joins

```python
import sqlite3

# Connect to one database
conn = sqlite3.connect('./plantnet_gbif.db')

# Attach the second database
conn.execute("ATTACH DATABASE './plantnet_counts.db' AS counts")

# Now you can join across databases!
cursor = conn.cursor()
cursor.execute("""
    SELECT 
        o.species_normalized,
        COUNT(o.gbifID) as observations,
        COALESCE(c.checked_count, 0) as images
    FROM occurrences o
    LEFT JOIN counts.image_counts c 
        ON o.species_normalized = c.directory
    WHERE o.countryCode = 'FR'
    GROUP BY o.species_normalized
    ORDER BY observations DESC
    LIMIT 20
""")

for species, obs, imgs in cursor.fetchall():
    print(f"{species:40} {obs:5} obs  {imgs:5} images")

conn.close()
```

## Troubleshooting

### "Database not found" Error

```
Error: Database not found or invalid
```

**Solution:** Create the databases first:
```bash
python src/parse_gbif_db.py --create
python src/parse_counts_db.py --create
```

### "No such table" Error

```
sqlite3.OperationalError: no such table: occurrences
```

**Solution:** Recreate the database with the latest schema:
```bash
python src/parse_gbif_db.py --create
```

### Database is Locked

```
sqlite3.OperationalError: database is locked
```

**Solution:** Close any other programs accessing the database, or use a different database file.

### Slow Queries

If queries are slow:
1. Make sure indexes were created (check with `--info`)
2. Rebuild database: `python src/parse_gbif_db.py --create`
3. Use `EXPLAIN QUERY PLAN` in sqlite3 to diagnose

## License

These scripts are provided as-is for educational and research purposes.
