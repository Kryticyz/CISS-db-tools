# PlantNet Image Mining Toolkit

A comprehensive toolkit for mining, analyzing, and managing plant species images from PlantNet via GBIF (Global Biodiversity Information Facility) data exports.

**Author:** Tynan Matthews
**Email:** tynan@matthews.solutions

---

## Table of Contents

- [What is PlantNet?](#what-is-plantnet)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [CLI Reference](#cli-reference)
- [Image Processing Pipeline](#image-processing-pipeline)
- [Common Workflows](#common-workflows)
- [Python API Usage](#python-api-usage)
- [Architecture](#architecture)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License & Resources](#license--resources)

---

## What is PlantNet?

[PlantNet](https://plantnet.org) is a citizen science platform where users upload photos of plants for identification. These observations are shared with [GBIF](https://www.gbif.org) (Global Biodiversity Information Facility), creating one of the largest open plant image datasets available.

This toolkit helps you:
- Download and organize PlantNet images by species
- Remove duplicate images using perceptual hashing
- Find visually similar images using CNN embeddings
- Detect outlier images that may be misclassified
- Visually review results through a web interface

---

## Key Features

- **Parse GBIF Data** - Load and query PlantNet observation and multimedia records
- **Build SQLite Databases** - Fast local querying of millions of records
- **Batch Image Downloads** - Rate-limited parallel downloading with species organization
- **Duplicate Detection** - Find exact and near-duplicate images using perceptual hashing
- **Similarity Analysis** - CNN-based image similarity using ResNet embeddings and FAISS
- **Outlier Detection** - Statistical analysis to find potentially misclassified images
- **Visual Review** - Modern web interface (FastAPI + React) for reviewing results
- **CLI Tools** - Full command-line interface for all operations

---

## Quick Start

### Prerequisites
- macOS 10.15+ (Apple Silicon or Intel)
- Conda/Miniconda
- 40 GB free disk space

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/plantnet.git
cd plantnet

# Create conda environment
conda env create -f environment.yml
conda activate plantnet

# Install package
pip install -e .

# Verify installation
plantnet --version
```

### 2. Download GBIF Data

1. Visit https://www.gbif.org
2. Search for "PlantNet" dataset
3. Download the Darwin Core Archive
4. Extract to `data/raw/gbif/`

> **Note:** GBIF data cannot be redistributed. Each user must download their own copy.

### 3. Build Database

```bash
plantnet-db-build --create
# Or: python scripts/data_processing/parse_gbif_db.py --create
```

### 4. Query and Download Images

```bash
# Query database
plantnet-db-query --summary
plantnet-db-query --species "Acacia_dealbata"

# Download images for a species
plantnet-download "Acacia_dealbata" --limit 100
```

### 5. Process and Review Images

```bash
# Deduplicate images
plantnet-deduplicate data/images/by_species/Acacia_dealbata

# Start visual review interface
plantnet-review data/images/by_species
# Open http://localhost:8000 in your browser
```

---

## Installation

### Quick Install (Conda)

```bash
conda env create -f environment.yml
conda activate plantnet
pip install -e .
```

### Why Conda?

This project uses **conda** to solve critical dependency issues:

- **Eliminates OpenMP conflicts** - Single unified library for PyTorch, NumPy, and FAISS
- **Fixes Python 3.13 MPS crashes** - Uses stable Python 3.11
- **Better dependency management** - Conda resolves complex C++ library dependencies

See [Installation Guide](docs/installation.md) for detailed instructions and troubleshooting.

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| OS | macOS 10.15+ | macOS 12+ |
| RAM | 8 GB | 16 GB |
| Disk | 40 GB free | 100 GB free |
| Python | 3.11 (via conda) | 3.11 |

---

## Project Structure

```
plantNet/
├── README.md                          # This file
├── CLAUDE.md                          # AI assistant guidance
├── environment.yml                    # Conda environment specification
├── pyproject.toml                     # Package configuration and CLI entry points
│
├── src/plantnet/                      # Installable Python package
│   ├── cli/                           # Command-line interface
│   │   ├── main.py                    # Main CLI dispatcher
│   │   ├── database_cmds.py           # Database CLI commands
│   │   ├── image_cmds.py              # Image CLI commands
│   │   └── analysis_cmds.py           # Analysis CLI commands
│   ├── core/                          # Core functionality
│   │   └── gbif_parser.py             # GBIF data parser
│   ├── images/                        # Image processing modules
│   │   ├── deduplication.py           # Perceptual hash deduplication
│   │   └── similarity.py              # CNN similarity analysis
│   ├── database/                      # Database operations
│   ├── web/                           # Web review application
│   └── utils/                         # Shared utilities
│       └── paths.py                   # Path configuration
│
├── scripts/                           # Standalone executable scripts
│   ├── data_processing/               # Data parsing and DB creation
│   │   ├── parse_gbif_db.py           # Build GBIF SQLite database
│   │   └── parse_counts_db.py         # Build image counts database
│   │
│   ├── database/                      # Database query tools
│   │   ├── query_unified_db.py        # Query both databases
│   │   ├── query_gbif.py              # Query GBIF data
│   │   ├── query_counts.py            # Query image counts
│   │   └── query_low_count_species.py # Find low-count species
│   │
│   ├── images/                        # Image operations
│   │   ├── batch_download_images.py   # Batch download with rate limiting
│   │   ├── batch_get_species_urls.py  # Extract URLs for species
│   │   ├── deduplicate_images.py      # Perceptual hash deduplication
│   │   ├── cnn_similarity.py          # CNN-based similarity detection
│   │   ├── batch_generate_embeddings.py # Pre-compute embeddings
│   │   ├── detect_outliers.py         # Statistical outlier detection
│   │   │
│   │   ├── review_app/                # Core detection modules
│   │   │   └── core/
│   │   │       ├── api.py             # High-level DetectionAPI
│   │   │       ├── detection.py       # Detection algorithms
│   │   │       └── storage.py         # FAISS embedding store
│   │   │
│   │   └── review_app_v3/             # Modern web application
│   │       ├── main.py                # FastAPI application
│   │       ├── api/                   # REST API routes
│   │       ├── services/              # Business logic layer
│   │       ├── models/                # Pydantic models
│   │       └── frontend/              # React frontend
│   │
│   ├── synonyms/                      # Species synonym tools
│   │   └── find_synonyms_gbif.py      # GBIF API synonym resolution
│   │
│   └── reports/                       # Report generation
│       └── generate_report_v3.py      # Species analysis reports
│
├── docs/                              # Documentation
│   ├── installation.md                # Detailed installation guide
│   ├── quickstart.md                  # 5-minute quick start
│   ├── DATABASE_GUIDE.md              # SQLite database usage
│   ├── GBIF_GUIDE.md                  # GBIF data guide
│   └── ...
│
├── tests/                             # Test suite
│   ├── test_core/                     # Core module tests
│   ├── test_images/                   # Image processing tests
│   └── ...
│
└── data/                              # Data files (gitignored)
    ├── raw/gbif/                      # GBIF export files
    │   ├── multimedia.txt             # Image metadata (~3.2M records)
    │   └── occurrence.txt             # Observations (~2.6M records)
    ├── databases/                     # SQLite databases
    │   ├── plantnet_gbif.db           # GBIF data
    │   ├── plantnet_counts.db         # Image counts
    │   └── embeddings/                # FAISS indices
    ├── processed/                     # Processed data
    │   ├── species_urls/              # URL files by species
    │   └── synonyms/                  # Synonym mappings
    └── images/by_species/             # Downloaded images
```

---

## CLI Reference

All CLI tools are installed via `pip install -e .`:

| Command | Description |
|---------|-------------|
| `plantnet` | Main CLI with subcommands |
| `plantnet-db-build` | Build SQLite databases from GBIF data |
| `plantnet-db-query` | Query databases for species and statistics |
| `plantnet-download` | Download images for species |
| `plantnet-deduplicate` | Find and mark duplicate images |
| `plantnet-embeddings` | Generate CNN embeddings for similarity search |
| `plantnet-review` | Start visual review web interface |

### Examples

```bash
# Database operations
plantnet-db-build --create                    # Build GBIF database
plantnet-db-query --summary                   # Database statistics
plantnet-db-query --species "Acacia_dealbata" # Search species

# Image operations
plantnet-download "Acacia_dealbata" --limit 100
plantnet-deduplicate data/images/by_species/Acacia_dealbata
plantnet-embeddings data/images/by_species/ --batch

# Review interface
plantnet-review data/images/by_species --port 8000
```

Use `--help` with any command for detailed options.

---

## Image Processing Pipeline

The toolkit provides a complete pipeline for image curation:

```
Download → Embed → Deduplicate → Find Similar → Detect Outliers → Review
```

### 1. Download Images

```bash
# Get URLs from GBIF database
python scripts/images/batch_get_species_urls.py species_list.txt --limit 400

# Download with rate limiting
python scripts/images/batch_download_images.py --workers 5 --delay 1
```

### 2. Generate Embeddings (Optional)

Pre-computing embeddings speeds up similarity search:

```bash
python scripts/images/batch_generate_embeddings.py data/images/by_species/
```

Embeddings are stored in `data/databases/embeddings/` for instant reuse.

### 3. Detect Duplicates

Uses perceptual hashing (pHash, dHash, aHash) to find exact and near-duplicates:

```bash
plantnet-deduplicate data/images/by_species/Acacia_dealbata --threshold 5
```

### 4. Find Similar Images

Uses ResNet CNN embeddings and FAISS for fast similarity search:

```bash
python scripts/images/cnn_similarity.py data/images/by_species/Acacia_dealbata --threshold 0.85
```

### 5. Detect Outliers

Statistical analysis to find images that don't fit the species:

```bash
python scripts/images/detect_outliers.py data/images/by_species/Acacia_dealbata
```

### 6. Visual Review

Web interface for reviewing all detection results:

```bash
# Modern FastAPI + React interface
python scripts/images/review_app_v3/main.py data/images/by_species

# Or legacy interface
plantnet-review data/images/by_species
```

Open http://localhost:8000 to:
- View duplicate groups
- Review similar image clusters
- Examine detected outliers
- Queue images for deletion

---

## Common Workflows

### Workflow 1: Setup from Scratch

```bash
# 1. Create environment
conda env create -f environment.yml
conda activate plantnet
pip install -e .

# 2. Place GBIF data in data/raw/gbif/

# 3. Build databases
python scripts/data_processing/parse_gbif_db.py --create
python scripts/data_processing/parse_counts_db.py --create

# 4. Verify
plantnet-db-query --summary
```

### Workflow 2: Process New Species

```bash
# 1. Create species list
echo "Eucalyptus_globulus" > species_list.txt

# 2. Get URLs and download
python scripts/images/batch_get_species_urls.py species_list.txt --limit 400
python scripts/images/batch_download_images.py --workers 5 --delay 1

# 3. Deduplicate
plantnet-deduplicate data/images/by_species/Eucalyptus_globulus

# 4. Review
plantnet-review data/images/by_species
```

### Workflow 3: Full Image Curation

```bash
# 1. Generate embeddings for fast similarity search
python scripts/images/batch_generate_embeddings.py data/images/by_species/

# 2. Start review app (detects duplicates, similar, and outliers)
python scripts/images/review_app_v3/main.py data/images/by_species

# 3. Review and curate in browser at http://localhost:8000
```

### Workflow 4: Analyze Coverage

```bash
# Compare GBIF vs local image counts
python scripts/database/query_unified_db.py --compare-coverage --limit 50

# Find species needing more images
python scripts/database/query_low_count_species.py --threshold 400

# Generate report
python scripts/reports/generate_report_v3.py
```

---

## Python API Usage

Use PlantNet as a library in your own code:

```python
# Parse GBIF data
from plantnet import GBIFParser

parser = GBIFParser()
parser.load_all()
multimedia = parser.get_multimedia()
print(f"Loaded {len(multimedia)} multimedia records")

# Deduplicate images
from plantnet.images import deduplicate_species_images

result = deduplicate_species_images(
    species_directory="data/images/by_species/Acacia_dealbata",
    hamming_threshold=5,
    verbose=True
)
print(f"Total: {result.total_images}, Duplicates: {result.duplicates_marked}")

# Find similar images
from plantnet.images import analyze_species_similarity

result = analyze_species_similarity(
    species_directory="data/images/by_species/Acacia_dealbata",
    similarity_threshold=0.85
)
print(f"Found {result.similar_groups} similar groups")

# Use detection API directly
from scripts.images.review_app.core.api import DetectionAPI

api = DetectionAPI("data/images/by_species")
duplicates = api.get_duplicate_groups("Acacia_dealbata")
similar = api.get_similar_groups("Acacia_dealbata", threshold=0.85)
outliers = api.get_outliers("Acacia_dealbata")
```

---

## Architecture

### Package vs Scripts

- **`src/plantnet/`** - Installable package with CLI entry points. Import with `from plantnet import ...`
- **`scripts/`** - Standalone scripts for batch operations. Run directly with `python scripts/...`

### Review App Versions

- **review_app_v3** (Modern) - FastAPI backend + React frontend. Full-featured with deletion queue
- **review_app** (Core) - Detection modules used by both versions
- **review_duplicates_v2.py** (Legacy) - Simple single-file web server

### Data Flow

```
GBIF Export → parse_gbif_db.py → SQLite Database
                                       ↓
                              batch_get_species_urls.py
                                       ↓
                              batch_download_images.py
                                       ↓
                              Images organized by species
                                       ↓
              ┌────────────────────────┼────────────────────────┐
              ↓                        ↓                        ↓
    deduplicate_images.py    cnn_similarity.py        detect_outliers.py
    (perceptual hashing)     (CNN + FAISS)            (statistical)
              ↓                        ↓                        ↓
              └────────────────────────┼────────────────────────┘
                                       ↓
                              review_app_v3 (web UI)
                                       ↓
                              Curated image dataset
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_imports.py

# Run with coverage
pytest --cov=plantnet --cov-report=term-missing

# Run image processing tests
pytest scripts/images/tests/

# Test database creation with subset
python scripts/data_processing/parse_gbif_db.py --create --max-rows 10000
```

---

## Documentation

Detailed guides are available in `docs/`:

| Guide | Description |
|-------|-------------|
| [Installation Guide](docs/installation.md) | Detailed setup and troubleshooting |
| [Quick Start](docs/quickstart.md) | 5-minute tutorial |
| [Database Guide](docs/DATABASE_GUIDE.md) | SQLite database usage |
| [GBIF Guide](docs/GBIF_GUIDE.md) | Working with GBIF data |
| [Counts Parser](docs/COUNTS_PARSER.md) | Image count CSV parsing |
| [Low Count Species](docs/LOW_COUNT_SPECIES.md) | Finding species with few images |

---

## Contributing

This is a research project. To contribute:

1. Document issues with reproducible steps
2. Ensure paths are correctly configured for your setup
3. Run from the project root directory
4. Run tests before submitting: `pytest`
5. Format code: `black .` and `ruff check .`

Open a GitHub issue or submit a pull request.

---

## License & Resources

This toolkit is provided as-is for educational and research purposes.

**Important:** GBIF data has its own licensing. Always check and respect the licenses of individual observations and images. Most PlantNet images are under Creative Commons licenses (CC-BY, CC-BY-SA, etc.).

### Resources

- [GBIF Website](https://www.gbif.org)
- [PlantNet](https://plantnet.org)
- [PlantNet on GBIF](https://www.gbif.org/dataset/7a3679ef-5582-4aaa-81f0-8c2545cafc81)

---

## Tips

1. **Always run from project root** - Path references assume you're in the `plantNet/` directory
2. **Use conda environment** - Always `conda activate plantnet` before running commands
3. **Start with small datasets** - Use `--max-rows` and `--limit` options when testing
4. **Be nice to servers** - Use `--delay` and reasonable `--workers` counts when downloading
5. **Check CLI help** - Every command has `--help` for detailed options

---

**Last Updated:** December 2025
