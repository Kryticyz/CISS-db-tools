# Archive

This directory contains archived code from previous project structures.

## scripts_old/

**Archived:** 2025-12-15  
**Reason:** Conda migration with project restructuring (v1.0.0)

Contains the original `scripts/` directory from before the conda migration and package restructuring.

### What was migrated:

**Core modules → `src/plantnet/core/`:**
- `scripts/data_processing/parse_gbif.py` → `src/plantnet/core/gbif_parser.py`

**Image processing → `src/plantnet/images/`:**
- `scripts/images/deduplicate_images.py` → `src/plantnet/images/deduplication.py`
- `scripts/images/cnn_similarity.py` → `src/plantnet/images/similarity.py`

**Web interface → `src/plantnet/web/`:**
- `scripts/images/review_duplicates.py` → `src/plantnet/web/review_app.py`

**Batch workflows → `workflows/batch/`:**
- `scripts/images/batch_download_images.py` → `workflows/batch/batch_download.py`
- `scripts/images/batch_generate_embeddings.py` → `workflows/batch/batch_embeddings.py`

**CLI commands → `src/plantnet/cli/`:**
- All `main()` functions extracted to dedicated CLI modules
- Registered as console scripts in `pyproject.toml`

### Why archived (not deleted):

1. **Git history preservation** - Keeps the original implementation for reference
2. **Migration verification** - Can diff against new implementation if needed
3. **Backward compatibility** - Some external tools may still reference old paths
4. **Documentation** - Useful for understanding the evolution of the codebase

### Using the new structure:

Instead of:
```bash
python scripts/images/deduplicate_images.py /path/to/species
```

Use:
```bash
plantnet-deduplicate /path/to/species
```

Or programmatically:
```python
from plantnet.images import deduplicate_species_images
result = deduplicate_species_images("/path/to/species")
```

### Migration notes:

All functionality has been preserved in the new structure:
- ✅ Updated imports to use `plantnet.*` package
- ✅ Centralized path management via `plantnet.utils.paths`
- ✅ CLI entry points for all commands
- ✅ Maintained backward compatibility where possible
- ✅ Improved error handling and documentation

### Cleanup plan:

**Do NOT delete** until:
- All users have migrated to new CLI commands
- External tools updated to use new paths
- Documentation fully updated
- At least one release cycle completed (v1.0.0 → v2.0.0)

Estimated deletion: 2026-12-15 (1 year retention)

---

**If you need functionality from archived scripts:**
Please use the new package structure instead. The archived scripts are no longer maintained and may have security or compatibility issues.

For help migrating:
- See `docs/installation.md` for new installation instructions
- See `docs/quickstart.md` for new usage examples
- See `workflows/README.md` for batch processing workflows
