# GBIF PlantNet Data Parser and Query Tools

This directory contains Python scripts for parsing and querying GBIF (Global Biodiversity Information Facility) PlantNet export data.

## Overview

The GBIF PlantNet dataset contains biodiversity observations from the PlantNet community, including:
- **occurrence.txt**: ~2.6M plant observation records with detailed taxonomic, geographic, and temporal information (226 columns)
- **multimedia.txt**: ~3.2M multimedia records (primarily images) associated with observations (15 columns)

## Files

- `parse_gbif.py` - Core parser library for loading and querying GBIF data
- `query_gbif.py` - Interactive CLI tool for querying the data
- `README_GBIF.md` - This file

## Requirements

- Python 3.7+
- Standard library only (no external dependencies required)

## Quick Start

### Test the Installation

```bash
# Run test suite with 100 rows
cd plantNet
python scripts/reports/test_gbif.py
# Enter: 100
```

### Basic Usage

```bash
# Display summary statistics
python scripts/database/query_gbif.py --summary

# Search for a species
python scripts/database/query_gbif.py --species "Acacia_dealbata"

# Get observations from a specific country
python scripts/database/query_gbif.py --country FR

# View a specific observation
python scripts/database/query_gbif.py --observation 2644196009

# See top contributing users
python scripts/database/query_gbif.py --top-users 20
```

## Data Structure

### Occurrence Records (occurrence.txt)

Each occurrence record contains 226 fields including:
- **Identifiers**: gbifID, occurrenceID, catalogNumber
- **Taxonomy**: scientificName, kingdom, phylum, class, order, family, genus, species
- **Location**: countryCode, stateProvince, locality, decimalLatitude, decimalLongitude, elevation
- **Temporal**: eventDate, year, month, day
- **Observer**: recordedBy, individualCount
- **Status**: basisOfRecord, occurrenceStatus
- **Reference**: references, license

### Multimedia Records (multimedia.txt)

Each multimedia record contains 15 fields:
- **gbifID**: Links to occurrence record
- **type**: Usually "StillImage"
- **format**: Image format (e.g., "image/jpeg")
- **identifier**: URL to the image
- **title**: Image description (e.g., "Acacia dealbata: flower")
- **creator**: Username of image contributor
- **created**: Timestamp when image was created
- **license**: Image license (e.g., "CC_BY_4_0")

## Command-Line Interface

### query_gbif.py

Interactive CLI tool for querying GBIF data.

#### Global Options

```bash
--gbif-dir PATH         Path to GBIF directory (default: ./plantnet_gbif)
--max-rows N           Load only N rows per file (for testing)
--limit N              Limit number of results to display
--count                Show counts/summary instead of full details
--details              Show additional details
--show-images          Include image information in output
```

#### Commands

##### Summary Statistics

```bash
python query_gbif.py --summary
```

Shows:
- Total occurrences and multimedia records
- Unique observations, species, countries, users
- Top 10 species, countries, and contributors

##### Species Search

```bash
# Basic search
python query_gbif.py --species "Acacia"

# Show with images
python query_gbif.py --species "Acacia dealbata" --show-images

# Limit results
python query_gbif.py --species "Acacia" --limit 50
```

Searches for observations by species name (case-insensitive partial match).

##### Country Search

```bash
# Basic country query
python query_gbif.py --country FR

# Show top species in country
python query_gbif.py --country FR --top-species 20

# Show sample observations
python query_gbif.py --country ES --details
```

Filter observations by ISO country code (e.g., FR, ES, IT, DE).

##### User/Contributor Search

```bash
# Search by username
python query_gbif.py --user "john"

# Show count by user
python query_gbif.py --user "john" --count

# Limit results
python query_gbif.py --user "smith" --limit 100
```

Search multimedia records by creator/contributor name.

##### Observation Details

```bash
# Show complete observation
python query_gbif.py --observation 2644196009

# Show without images
python query_gbif.py --observation 2644196009 --count
```

Display complete details for a specific GBIF ID including taxonomy, location, temporal info, and associated images.

##### Date Range Filtering

```bash
# Filter by date range
python query_gbif.py --date-range 2019-10-01 2019-10-31

# Just show count
python query_gbif.py --date-range 2020-01-01 2020-12-31 --count
```

Filter observations within a date range (YYYY-MM-DD format).

##### Top Lists

```bash
# Top species
python query_gbif.py --top-species 20

# Top species with geographic distribution
python query_gbif.py --top-species 10 --details

# Top countries
python query_gbif.py --top-countries 20

# Top contributors
python query_gbif.py --top-users 50
```

Show ranked lists by observation/image counts.

##### Detailed Statistics

```bash
python query_gbif.py --stats
```

Show comprehensive statistics about the dataset.

## Python API

### parse_gbif.py

Core library for programmatic access to GBIF data.

#### Basic Usage

```python
from parse_gbif import GBIFParser

# Initialize parser
parser = GBIFParser(gbif_dir="./plantnet_gbif")

# Load data
parser.load_all()

# Or load with limit for testing
parser.load_all(max_rows=10000)
```

## Data Access Features

### Parser Library (`parse_gbif.py`)

**Data Loading:**
- `load_multimedia()` - Load image records
- `load_occurrences()` - Load observation records
- `load_all()` - Load both files
- Supports `max_rows` parameter for testing

**Lookup Methods:**
- `get_images_by_gbif_id(id)` - Get all images for an observation
- `get_occurrence_by_gbif_id(id)` - Get observation details
- `get_complete_observation(id)` - Get everything for an observation

**Search Methods:**
- `search_by_species(name)` - Find observations by species
- `search_by_country(code)` - Find observations by country
- `search_by_user(name)` - Find images by creator
- `filter_by_date_range(start, end)` - Filter by date

**Aggregation Methods:**
- `get_species_counts()` - Count observations per species
- `get_country_counts()` - Count observations per country
- `get_user_counts()` - Count images per user
- `get_top_species(n)` - Top N species
- `get_top_countries(n)` - Top N countries
- `get_top_users(n)` - Top N contributors
- `get_statistics()` - Overall statistics

### Query Tool (`query_gbif.py`)

**Commands:**
- `--summary` - Show dataset overview
- `--species NAME` - Search by species name
- `--country CODE` - Filter by country
- `--user NAME` - Search by contributor
- `--observation ID` - Show observation details
- `--date-range START END` - Filter by date range
- `--top-species N` - Top species list
- `--top-countries N` - Top countries list
- `--top-users N` - Top contributors list
- `--stats` - Detailed statistics

**Options:**
- `--limit N` - Limit results displayed
- `--count` - Show counts only
- `--details` - Show additional details
- `--show-images` - Include image information
- `--max-rows N` - Load subset (for testing)

## Examples

### Example 1: Find all Acacia observations in France

```bash
python query_gbif.py --species "Acacia" --country FR
```

Or in Python:

```python
from parse_gbif import GBIFParser

parser = GBIFParser()
parser.load_all()

# Get all Acacia observations
acacia_obs = parser.search_by_species("Acacia")

# Filter for France
french_acacia = [obs for obs in acacia_obs if obs.get('countryCode') == 'FR']

print(f"Found {len(french_acacia)} Acacia observations in France")
```

### Example 2: Analyze observations by a specific user

```bash
python query_gbif.py --user "john smith" --count
```

Or in Python:

```python
parser = GBIFParser()
parser.load_all()

user_images = parser.search_by_user("john smith")
print(f"User has contributed {len(user_images)} images")

# Get unique observations
unique_obs = set(img['gbifID'] for img in user_images)
print(f"Covering {len(unique_obs)} unique observations")
```

### Example 3: Monthly observation counts

```python
from parse_gbif import GBIFParser
from collections import defaultdict

parser = GBIFParser()
parser.load_all()

monthly_counts = defaultdict(int)
for obs in parser.get_occurrences():
    year = obs.get('year')
    month = obs.get('month')
    if year and month:
        key = f"{year}-{month:02d}"
        monthly_counts[key] += 1

# Print sorted by date
for month in sorted(monthly_counts.keys()):
    print(f"{month}: {monthly_counts[month]:,} observations")
```

### Example 4: Geographic distribution of a species

```python
from parse_gbif import GBIFParser

parser = GBIFParser()
parser.load_all()

species = "Acacia dealbata"
observations = parser.search_by_species(species)

# Count by country
countries = {}
for obs in observations:
    country = obs.get('countryCode')
    if country:
        countries[country] = countries.get(country, 0) + 1

print(f"\n{species} distribution:")
for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
    print(f"  {country}: {count:,} observations")
```

### Example 5: Image types analysis

```python
from parse_gbif import GBIFParser
from collections import Counter

parser = GBIFParser()
parser.load_all()

# Extract organ types from titles (e.g., "Species name: flower")
organ_types = []
for img in parser.get_multimedia():
    title = img.get('title', '')
    if ':' in title:
        organ = title.split(':')[-1].strip()
        organ_types.append(organ)

# Count most common
counter = Counter(organ_types)
print("\nMost common image types:")
for organ, count in counter.most_common(20):
    print(f"  {organ}: {count:,} images")
```

## Performance Notes

- **Loading time**: Full dataset (~5.8M rows) takes 2-5 minutes to load on typical hardware
- **Memory usage**: Approximately 2-3 GB RAM for full dataset
- **Testing**: Use `--max-rows` parameter to load subset of data for faster testing
- **Indexing**: Data is automatically indexed by gbifID for fast lookups

## Tips

1. **Test with small datasets first**: Use `--max-rows 10000` when developing queries
2. **Save results**: Pipe output to file for large result sets: `python query_gbif.py --species "Acacia" > results.txt`
3. **Combine filters**: Use Python API for complex multi-criteria queries
4. **Case sensitivity**: Most searches are case-insensitive by default
5. **Partial matching**: Species and user searches support partial name matching

## Troubleshooting

### File Not Found Error

```
Error: File not found: ./plantnet_gbif/multimedia.txt
```

**Solution**: Make sure you're in the correct directory or specify `--gbif-dir` path:
```bash
python query_gbif.py --gbif-dir /path/to/plantnet_gbif --summary
```

### Memory Issues

If you run out of memory loading the full dataset:
1. Use `--max-rows` to load a subset
2. Process data in chunks using Python API
3. Increase available RAM or use a machine with more memory

### Slow Performance

- First load is always slow due to file I/O
- Subsequent queries on loaded data are fast
- Consider creating a database if you need repeated access

## Data Source

This data is exported from GBIF (Global Biodiversity Information Facility) and represents observations from the PlantNet citizen science platform.

- GBIF Website: https://www.gbif.org
- PlantNet: https://plantnet.org
- License: Varies by observation (see individual license fields)

## Related Scripts

- `parse_counts.py` - Parser for image count CSV files
- `query_counts.py` - Query tool for image counts

## License

These scripts are provided as-is for educational and research purposes.
