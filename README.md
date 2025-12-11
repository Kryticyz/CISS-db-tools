# PlantNet Image Mining Project

A comprehensive toolkit for mining, analyzing, and managing plant species images from PlantNet via GBIF (Global Biodiversity Information Facility) data exports.

**Author:** Tynan Matthews  
**Email:** tynan@matthews.solutions

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Documentation](#documentation)
- [Common Workflows](#common-workflows)
- [Contributing](#contributing)

---

## Overview

This project provides tools to:

- **Parse GBIF PlantNet data** exports (occurrence and multimedia records)
- **Build SQLite databases** for fast querying of species observations and images
- **Extract image URLs** for specific plant species
- **Download images** in batch with species organization
- **Analyze image counts** and data coverage
- **Find synonyms** for species names using GBIF taxonomy
- **Generate reports** on species data availability

The toolkit is designed for researchers, data scientists, and developers working with plant biodiversity data and computer vision datasets.

---

## Project Structure

```
plantNet/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── docs/                              # Documentation
│   ├── DATABASE_GUIDE.md              # SQLite database usage
│   ├── GBIF_GUIDE.md                  # GBIF data parser guide
│   ├── COUNTS_PARSER.md               # Image count parser
│   ├── LOW_COUNT_SPECIES.md           # Low count species workflow
│   └── EXTRACT_DIRECTORIES.md         # Directory extraction tool
│
├── scripts/                           # Executable scripts
│   ├── data_processing/               # Data parsing and DB creation
│   │   ├── parse_counts.py            # Parse CSV image counts
│   │   ├── parse_counts_db.py         # Build counts database
│   │   ├── parse_gbif.py              # Parse GBIF text files
│   │   └── parse_gbif_db.py           # Build GBIF database
│   │
│   ├── database/                      # Database queries
│   │   ├── query_counts.py            # Query image counts
│   │   ├── query_gbif.py              # Query GBIF data
│   │   ├── query_unified_db.py        # Query both databases
│   │   ├── query_low_count_species.py # Find low-count species
│   │   └── low_count_species_query.sql # SQL query template
│   │
│   ├── synonyms/                      # Species synonym tools
│   │   ├── find_synonyms.py           # Find synonyms using LLM (not recommended)
│   │   ├── find_synonyms_gbif.py      # Find synonyms via GBIF API
│   │   └── check_synonyms.sh          # Check synonym mismatches
│   │
│   ├── images/                        # Image download tools
│   │   ├── download_image.py          # Download single image
│   │   ├── batch_download_images.py   # Batch download by species
│   │   ├── get_species_urls.py        # Get URLs for one species
│   │   └── batch_get_species_urls.py  # Get URLs for multiple species
│   │
│   ├── directories/                   # Directory utilities
│   │   └── extract_directories.sh     # Extract directory names from CSV
│   │
│   └── reports/                       # Report generation
│       ├── generate_report_v3.py      # Species analysis report
│       └── test_gbif.py               # GBIF parser tests
│
└── data/                              # Data files (gitignored)
    ├── raw/                           # Original source data
    │   └── gbif/                      # GBIF export files
    │       ├── multimedia.txt         # Image metadata (~3.2M records)
    │       ├── occurrence.txt         # Observations (~2.6M records)
    │       └── ...                    # Other GBIF files
    │
    ├── processed/                     # Processed/transformed data
    │   ├── counts/                    # Image count CSV files
    │   │   ├── original_image_counts.csv
    │   │   ├── cleaned_checked_image_counts.csv
    │   │   └── cleaned_unchecked_image_counts.csv
    │   │
    │   ├── species_urls/              # URL files by species
    │   │   ├── Acacia_dealbata_urls.txt
    │   │   └── ...
    │   │
    │   └── synonyms/                  # Species synonym data
    │       ├── species_synonyms_gbif.csv
    │       ├── species_synonyms_gbif.json
    │       └── species_synonyms_gbif.txt
    │
    ├── databases/                     # SQLite databases
    │   ├── plantnet_gbif.db          # GBIF observations & images
    │   └── plantnet_counts.db        # Local image counts
    │
    ├── images/                        # Downloaded images
    │   ├── by_species/               # Organized by species
    │   │   ├── Acacia_dealbata/
    │   │   └── ...
    │   └── uncategorized/            # Loose images
    │
    └── reports/                       # Generated reports & outputs
        ├── FINAL_REPORT_v3.md
        ├── species_report_v3.csv
        ├── species_list.txt
        └── ...
```

---

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Download GBIF Data

Download PlantNet data from GBIF:
1. Visit https://www.gbif.org
2. Search for "PlantNet" dataset
3. Download the Darwin Core Archive
4. Extract to `data/raw/gbif/`

**Note:** GBIF data cannot be redistributed, so each user must download their own copy.

### 3. Build Databases

```bash
# Build GBIF database (took 10 minutes for full dataset on my Macbook Pro M4)
python scripts/data_processing/parse_gbif_db.py --create

# Build counts database (if you have image count CSVs)
python scripts/data_processing/parse_counts_db.py --create
```

### 4. Query Data

```bash
# Summary of both databases
python scripts/database/query_unified_db.py --summary

# Search for a specific species
python scripts/database/query_unified_db.py --species "Acacia_dealbata" --details

# Find species in a country
python scripts/database/query_gbif.py --country AU --limit 50
```

### 5. Download Images

```bash
# Get image URLs for species (from species_list.txt)
python scripts/images/batch_get_species_urls.py data/reports/species_list.txt

# Download images for all species
python scripts/images/batch_download_images.py
```

---

## Installation

### Requirements

- **Python 3.7+**
- **SQLite 3** (included with Python)

### Python Packages

```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` - For downloading images and GBIF API calls
- Standard library only for core functionality

---

## Documentation

Detailed guides (generated via LLMs) are available in the `docs/` directory:

- **[DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)** - Complete guide to SQLite database tools
- **[GBIF_GUIDE.md](docs/GBIF_GUIDE.md)** - Working with GBIF PlantNet data
- **[COUNTS_PARSER.md](docs/COUNTS_PARSER.md)** - Parsing image count CSV files
- **[LOW_COUNT_SPECIES.md](docs/LOW_COUNT_SPECIES.md)** - Finding species with low image counts
- **[EXTRACT_DIRECTORIES.md](docs/EXTRACT_DIRECTORIES.md)** - Directory name extraction utilities

---

## Common Workflows

### Workflow 1: Complete Setup from Scratch

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place GBIF data in data/raw/gbif/

# 3. Build databases
python scripts/data_processing/parse_gbif_db.py --create
python scripts/data_processing/parse_counts_db.py --create

# 4. Verify data
python scripts/database/query_unified_db.py --summary
```

### Workflow 2: Find and Download Images for Species

```bash
# 1. Create species list (or use existing)
echo "Acacia_dealbata" > data/reports/species_list.txt
echo "Eucalyptus_globulus" >> data/reports/species_list.txt

# 2. Get image URLs from GBIF
python scripts/images/batch_get_species_urls.py data/reports/species_list.txt --limit 400

# 3. Download images - We found success using 400 workers but ran into timeout errors at 900+, your results will depend on your network connection and computers available resources
python scripts/images/batch_download_images.py --workers 5 --delay 1
```

### Workflow 3: Analyze Species Coverage

```bash
# Compare coverage between GBIF and local counts
python scripts/database/query_unified_db.py --compare-coverage --limit 50

# Find species with low image counts
python scripts/database/query_low_count_species.py --threshold 400 --output low_count.csv

# Generate comprehensive report
python scripts/reports/generate_report_v3.py
```

### Workflow 4: Find Synonyms for Species

```bash
# Find species without images
python scripts/synonyms/find_synonyms_gbif.py data/reports/no_images.txt

# Check for mismatches
bash scripts/synonyms/check_synonyms.sh
```

---

## Script Usage Examples

### Query GBIF Data

```bash
# Show summary statistics
python scripts/database/query_gbif.py --summary

# Search for species
python scripts/database/query_gbif.py --species "Acacia dealbata" --show-images

# Filter by country
python scripts/database/query_gbif.py --country FR --top-species 20

# View specific observation
python scripts/database/query_gbif.py --observation 2644196009
```

### Query Image Counts

```bash
# Show summary
python scripts/database/query_counts.py --summary

# Search directories
python scripts/database/query_counts.py --search "Acacia"

# Top species by count
python scripts/database/query_counts.py --top 20 --dataset checked
```

### Download Images

```bash
# Single species
python scripts/images/get_species_urls.py "Acacia dealbata" --limit 400 > acacia_urls.txt

# Batch download with options
python scripts/images/batch_download_images.py \
  --workers 10 \
  --delay 1 \
  --limit 50 \
  --output data/images/by_species
```

---

## Testing

```bash
# Test GBIF parser with small dataset
python scripts/reports/test_gbif.py
# Enter max rows when prompted (e.g., 1000)

# Test database creation with subset
python scripts/data_processing/parse_gbif_db.py --create --max-rows 10000
```

---

## Contributing

This is a research project. If you find bugs or have suggestions:

1. Document the issue with reproducible steps
2. Check if paths are correctly configured for your setup
3. Ensure you're running from the project root directory
4. If still not resolved, open a github issue on this repo outlining the steps to reproduce. You are welcome to submit a pull request if you have fixed the issue yourself.

---

## License

This toolkit is provided as-is for educational and research purposes.

**Important:** GBIF data has its own licensing. Always check and respect the licenses of individual observations and images. Most PlantNet images are under Creative Commons licenses (CC-BY, CC-BY-SA, etc.).

---

## Resources

- **GBIF Website:** https://www.gbif.org
- **PlantNet:** https://plantnet.org
- **PlantNet on GBIF:** https://www.gbif.org/dataset/7a3679ef-5582-4aaa-81f0-8c2545cafc81

---

## Tips

1. **Always run scripts from the project root** - Path references assume you're in the `plantNet/` directory
2. **Use virtual environments** - Keeps dependencies isolated
3. **Start with small datasets** - Use `--max-rows` options when testing
4. **Be nice to servers** - Use `--delay` and reasonable `--workers` counts when downloading
5. **Check documentation** - Each script has `--help` for detailed options

---

**Last Updated:** 2025
