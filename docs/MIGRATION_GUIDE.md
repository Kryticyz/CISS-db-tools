# Migration Guide - Project Reorganization

This guide helps you migrate from the old project structure to the new organized structure.

## Overview of Changes

The project has been reorganized to follow best practices for Python projects:

- **Scripts** are now in `scripts/` subdirectories organized by function
- **Documentation** is consolidated in `docs/`
- **Data** is organized in `data/` with clear hierarchy (raw → processed → databases → reports)
- **Paths** in all scripts have been updated to reflect new locations

## What Changed

### Directory Structure Changes

| Old Location | New Location | Description |
|-------------|--------------|-------------|
| `src/*.py` | `scripts/data_processing/` or `scripts/database/` | Python scripts organized by purpose |
| `src/docs/*.md` | `docs/*.md` | All documentation in one place |
| `plantnet_gbif/` | `data/raw/gbif/` | GBIF source data |
| `counts/*.csv` | `data/processed/counts/` | Image count CSV files |
| `species_urls/*.txt` | `data/processed/species_urls/` | Species URL files |
| `*.db` (root) | `data/databases/` | SQLite databases |
| `dump/*/` (species folders) | `data/images/by_species/` | Organized species images |
| `dump/*.jpg` (loose files) | `data/images/uncategorized/` | Uncategorized images |
| `data/*.txt`, `data/*.csv` | `data/reports/` | Generated reports and outputs |

### Script Organization

#### Data Processing Scripts
- `src/parse_counts.py` → `scripts/data_processing/parse_counts.py`
- `src/parse_counts_db.py` → `scripts/data_processing/parse_counts_db.py`
- `src/parse_gbif.py` → `scripts/data_processing/parse_gbif.py`
- `src/parse_gbif_db.py` → `scripts/data_processing/parse_gbif_db.py`

#### Database Query Scripts
- `src/query_counts.py` → `scripts/database/query_counts.py`
- `src/query_gbif.py` → `scripts/database/query_gbif.py`
- `src/query_unified_db.py` → `scripts/database/query_unified_db.py`
- `src/query_low_count_species.py` → `scripts/database/query_low_count_species.py`

#### Synonym Scripts
- `src/find_synonyms.py` → `scripts/synonyms/find_synonyms.py`
- `src/find_synonyms_gbif.py` → `scripts/synonyms/find_synonyms_gbif.py`
- `check_synonyms.sh` → `scripts/synonyms/check_synonyms.sh`

#### Image Scripts
- `src/download_image.py` → `scripts/images/download_image.py`
- `src/batch_download_images.py` → `scripts/images/batch_download_images.py`
- `src/get_species_urls.py` → `scripts/images/get_species_urls.py`
- `src/batch_get_species_urls.py` → `scripts/images/batch_get_species_urls.py`

#### Report Scripts
- `generate_report_v3.py` → `scripts/reports/generate_report_v3.py`
- `src/test_gbif.py` → `scripts/reports/test_gbif.py`

#### Utility Scripts
- `src/extract_directories.sh` → `scripts/directories/extract_directories.sh`

### Documentation Files

- `src/README_DB.md` → `docs/DATABASE_GUIDE.md`
- `src/README_GBIF.md` → `docs/GBIF_GUIDE.md`
- `src/docs/COUNTS_PARSER_README.md` → `docs/COUNTS_PARSER.md`
- `src/docs/QUICK_START_LOW_COUNT.md` → `docs/LOW_COUNT_SPECIES.md`
- `src/exract_dir_README.md` → `docs/EXTRACT_DIRECTORIES.md`

## Updated Default Paths

All scripts now use new default paths. If you run scripts from the **project root** (recommended), they will work without arguments:

### Old Defaults → New Defaults

```bash
# Databases
./plantnet_gbif.db          → ./data/databases/plantnet_gbif.db
./plantnet_counts.db        → ./data/databases/plantnet_counts.db

# GBIF data
./plantnet_gbif/            → ./data/raw/gbif/

# Image counts
./counts/                   → ./data/processed/counts/

# Species URLs
./species_urls/             → ./data/processed/species_urls/

# Downloaded images
./dump/                     → ./data/images/by_species/

# Reports
./species_list.txt          → ./data/reports/species_list.txt
./no_images.txt             → ./data/reports/no_images.txt
./species_synonyms_gbif.*   → ./data/processed/synonyms/species_synonyms_gbif.*
```

## Migration Steps

### Step 1: Update Your Working Directory

**Important:** Always run scripts from the project root directory:

```bash
cd /path/to/plantNet
```

### Step 2: Update Custom Scripts (If Any)

If you created custom scripts, update their paths:

**Old:**
```python
from parse_gbif import GBIFParser
parser = GBIFParser(gbif_dir="./plantnet_gbif")
conn = sqlite3.connect("./plantnet_gbif.db")
```

**New:**
```python
from parse_gbif import GBIFParser
parser = GBIFParser(gbif_dir="./data/raw/gbif")
conn = sqlite3.connect("./data/databases/plantnet_gbif.db")
```

### Step 3: Update Shell Scripts or Aliases

If you have shell scripts or aliases:

**Old:**
```bash
python src/query_gbif.py --species "Acacia"
python src/batch_download_images.py species_urls
```

**New:**
```bash
python scripts/database/query_gbif.py --species "Acacia"
python scripts/images/batch_download_images.py
```

### Step 4: Update Import Statements (If Importing Modules)

If you're importing modules in your own scripts:

**Old:**
```python
sys.path.append('src')
from parse_gbif import GBIFParser
```

**New:**
```python
sys.path.append('scripts/data_processing')
from parse_gbif import GBIFParser
```

**Note:** The reorganized scripts already handle this internally with proper path manipulation.

## Quick Command Reference

### Before (Old Structure)

```bash
# Build databases
python src/parse_gbif_db.py --create
python src/parse_counts_db.py --create

# Query data
python src/query_gbif.py --summary
python src/query_unified_db.py --summary

# Get URLs
python src/batch_get_species_urls.py species_list.txt

# Download images
python src/batch_download_images.py species_urls -o dump
```

### After (New Structure)

```bash
# Build databases (same commands, new locations)
python scripts/data_processing/parse_gbif_db.py --create
python scripts/data_processing/parse_counts_db.py --create

# Query data
python scripts/database/query_gbif.py --summary
python scripts/database/query_unified_db.py --summary

# Get URLs (note: defaults now point to data/reports/ and data/processed/)
python scripts/images/batch_get_species_urls.py data/reports/species_list.txt

# Download images (defaults to data/images/by_species)
python scripts/images/batch_download_images.py
```

## Common Issues and Solutions

### Issue 1: "Database not found"

**Symptom:**
```
Error: Database not found: ./plantnet_gbif.db
```

**Solution:**
Either regenerate the database in the new location or specify the old path:
```bash
# Option 1: Regenerate (recommended)
python scripts/data_processing/parse_gbif_db.py --create

# Option 2: Specify old path
python scripts/database/query_gbif.py --db-path ./plantnet_gbif.db --summary
```

### Issue 2: "Module not found" when importing

**Symptom:**
```python
ImportError: No module named 'parse_gbif'
```

**Solution:**
The scripts now handle imports internally. If you're importing in your own code:
```python
import sys
from pathlib import Path

# Add scripts/data_processing to path
sys.path.insert(0, str(Path(__file__).parent / "scripts" / "data_processing"))
from parse_gbif import GBIFParser
```

### Issue 3: "File not found" errors

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'species_urls/Acacia_dealbata_urls.txt'
```

**Solution:**
Make sure you're running from the project root:
```bash
cd /path/to/plantNet
python scripts/images/batch_download_images.py
```

### Issue 4: Old scripts still exist

**Symptom:**
You have both `src/query_gbif.py` and `scripts/database/query_gbif.py`

**Solution:**
The old directories should be empty. You can safely remove them:
```bash
# After verifying everything works
rm -rf src/
```

## Backward Compatibility

### Option 1: Symbolic Links (Unix/macOS/Linux)

Create symbolic links to maintain backward compatibility:

```bash
# Link old database locations to new ones
ln -s data/databases/plantnet_gbif.db plantnet_gbif.db
ln -s data/databases/plantnet_counts.db plantnet_counts.db

# Link old directories
ln -s data/raw/gbif plantnet_gbif
ln -s data/processed/counts counts
ln -s data/processed/species_urls species_urls
```

### Option 2: Specify Paths Explicitly

Always specify paths when calling scripts:

```bash
python scripts/database/query_gbif.py \
  --gbif-dir ./old_location/plantnet_gbif \
  --summary
```

## Testing the Migration

Run these commands to verify everything works:

```bash
# 1. Check if databases exist
ls -lh data/databases/

# 2. Test GBIF query
python scripts/database/query_gbif.py --summary

# 3. Test counts query
python scripts/database/query_counts.py --summary

# 4. Test unified query
python scripts/database/query_unified_db.py --summary

# 5. Generate test report
python scripts/reports/generate_report_v3.py
```

## Rollback (If Needed)

If you need to rollback:

1. Keep the old directory structure
2. Use the old git commit before reorganization
3. Or use explicit paths to access data in new locations

## Benefits of New Structure

✅ **Clear organization** - Easy to find what you need  
✅ **Scalable** - Easy to add new scripts or data types  
✅ **Professional** - Follows Python project best practices  
✅ **Better gitignore** - Only tracks source code, not generated data  
✅ **Separation of concerns** - Code, data, and docs are separate  

## Need Help?

If you encounter issues not covered here:

1. Check that you're in the project root directory: `pwd` should show `.../plantNet`
2. Verify paths with: `ls -la data/databases/`
3. Use `--help` flag on any script for usage information
4. Check the main [README.md](../README.md) for examples

---

**Migration completed on:** 2024  
**All scripts updated:** ✅  
**All paths updated:** ✅  
**Documentation updated:** ✅