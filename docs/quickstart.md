# Quick Start Guide

Get started with PlantNet in 5 minutes!

## Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/plantnet.git
cd plantnet

# Create conda environment
conda env create -f environment.yml
conda activate plantnet

# Install package
pip install -e .
```

## Verify Installation

```bash
# Check version
plantnet --version

# Test imports
python test_imports.py
```

## Basic Workflow

### 1. Prepare GBIF Data

Download PlantNet data from GBIF:
1. Visit https://www.gbif.org
2. Search for "PlantNet"
3. Download Darwin Core Archive
4. Extract to `data/raw/gbif/`

### 2. Build Databases

```bash
# Build GBIF database (takes ~10 minutes)
python scripts/data_processing/parse_gbif_db.py --create

# Or use CLI (coming soon)
plantnet-db-build --create
```

### 3. Query Species

```bash
# Python way
python scripts/database/query_unified_db.py --summary
python scripts/database/query_unified_db.py --species "Acacia dealbata"

# CLI way (coming soon)
plantnet-db-query --summary
```

### 4. Download Images

```bash
# Get URLs for species
python scripts/images/batch_get_species_urls.py species_list.txt

# Download images
python scripts/images/batch_download_images.py
```

### 5. Deduplicate Images

```bash
# Using CLI
plantnet-deduplicate data/images/by_species/Acacia_dealbata

# Or using Python
python -c "
from plantnet.images import deduplicate_species_images
result = deduplicate_species_images('data/images/by_species/Acacia_dealbata')
print(f'Found {result.duplicate_groups} duplicate groups')
"
```

### 6. Find Similar Images (CNN)

```bash
# Using CLI
plantnet-embeddings data/images/by_species/Acacia_dealbata --threshold 0.85

# Or using Python
python -c "
from plantnet.images import analyze_species_similarity
result = analyze_species_similarity('data/images/by_species/Acacia_dealbata')
print(f'Found {result.similar_groups} similar groups')
"
```

### 7. Visual Review Interface

```bash
# Start web server
python scripts/images/review_duplicates.py data/images/by_species

# Or use CLI (coming soon)
plantnet-review data/images/by_species

# Open http://localhost:8000 in browser
```

## Using as a Library

```python
# Import modules
from plantnet import GBIFParser, deduplicate_species_images
from plantnet.images import analyze_species_similarity
from plantnet.utils.paths import IMAGES_DIR, DATA_DIR

# Parse GBIF data
parser = GBIFParser()
parser.load_all()
multimedia = parser.get_multimedia()
print(f"Loaded {len(multimedia)} multimedia records")

# Deduplicate images
result = deduplicate_species_images(
    species_directory="data/images/by_species/Acacia_dealbata",
    hamming_threshold=5,
    verbose=True
)
print(f"Total: {result.total_images}")
print(f"Unique: {result.unique_images}")
print(f"Duplicates: {result.duplicates_marked}")

# Find similar images
result = analyze_species_similarity(
    species_directory="data/images/by_species/Acacia_dealbata",
    similarity_threshold=0.85,
    model_name="resnet18"
)
print(f"Similar groups: {result.similar_groups}")
```

## Common Tasks

### Add a New Species

```bash
# 1. Get URLs
python scripts/images/get_species_urls.py "Eucalyptus globulus"

# 2. Download images
python scripts/images/batch_download_images.py

# 3. Deduplicate
plantnet-deduplicate data/images/by_species/Eucalyptus_globulus
```

### Generate Report

```bash
python scripts/reports/generate_report_v3.py
```

### Find Species Synonyms

```bash
python scripts/synonyms/find_synonyms_gbif.py
```

## Troubleshooting

### Import errors

```bash
# Ensure package is installed
pip install -e .

# Ensure conda environment is activated
conda activate plantnet
```

### "FAISS not found"

```bash
conda install -c conda-forge faiss-cpu --force-reinstall
```

### MPS errors on Apple Silicon

The conda environment uses Python 3.11 which is stable. If you still have issues:

```bash
# Force CPU mode
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

## Next Steps

- Read the [User Guide](user_guide/) for detailed documentation
- Check [Installation Guide](installation.md) for troubleshooting
- Explore example workflows in `workflows/`

## Getting Help

- Check documentation in `docs/`
- Review script help: `python script.py --help`
- CLI help: `plantnet-command --help`

---

**You're all set!** Start exploring your plant image data with PlantNet.
