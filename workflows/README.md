# PlantNet Workflows

High-level orchestration scripts for batch processing and analysis tasks.

## Directory Structure

```
workflows/
├── batch/              # Batch processing workflows
│   ├── batch_download.py     # Batch image downloading from URLs
│   └── batch_embeddings.py   # Batch CNN embedding generation
├── analysis/           # Analysis and reporting workflows
└── data_processing/    # Data pipeline workflows
```

## Batch Workflows

### Batch Image Download

Download images for multiple species from URL files:

```bash
# Download all species
python workflows/batch/batch_download.py data/processed/species_urls

# Download with custom settings
python workflows/batch/batch_download.py data/processed/species_urls \
    --output data/images/by_species \
    --workers 10 \
    --delay 1

# Download specific species only
python workflows/batch/batch_download.py data/processed/species_urls \
    --species Acacia_baileyana Acacia_dealbata

# Save failed URLs for retry
python workflows/batch/batch_download.py data/processed/species_urls \
    --save-failed failed_urls.txt
```

**Features:**
- Concurrent downloads with configurable workers
- Automatic retry with exponential backoff
- Rate limiting with delay option
- Error handling for SSL, timeout, and connection issues
- Failed URL tracking for retry

### Batch Embedding Generation

Pre-compute CNN embeddings for all species images:

```bash
# Generate embeddings with default settings
python workflows/batch/batch_embeddings.py data/images/by_species

# Use larger model
python workflows/batch/batch_embeddings.py data/images/by_species \
    --model resnet50 \
    --batch-size 64

# Force CPU mode (for MPS stability issues)
python workflows/batch/batch_embeddings.py data/images/by_species --cpu

# Custom output location
python workflows/batch/batch_embeddings.py data/images/by_species \
    --output custom/embeddings/path
```

**Features:**
- Batch processing with configurable batch size
- Multiple model options (ResNet18, ResNet50, ResNet101)
- FAISS vector database creation
- Species statistics computation
- MPS/CPU mode selection
- Progress tracking with tqdm

**Output:**
Creates a FAISS database at `data/databases/embeddings/` with:
- `embeddings.index` - FAISS index for fast similarity search
- `metadata.pkl` - Image metadata (filename, species, path, size)
- `metadata_full.pkl` - Metadata with embeddings for outlier detection
- `species_stats.json` - Per-species statistics and centroids
- `summary.json` - Overall processing summary

## Integration with PlantNet Package

These workflows use the plantnet package for core functionality:

```python
# Workflows import from plantnet package
from plantnet.images.similarity import compute_cnn_embeddings_batch
from plantnet.utils.paths import EMBEDDINGS_DIR
```

This ensures:
- Consistent behavior with CLI tools
- Access to all package utilities
- Proper path management
- Shared configuration and defaults

## When to Use Workflows vs CLI

**Use Workflows when:**
- Processing large batches of data
- Running overnight/long-running tasks
- Need custom orchestration logic
- Require detailed progress tracking
- Want to save intermediate results

**Use CLI tools when:**
- Processing single species
- Interactive exploration
- Quick one-off tasks
- Testing and debugging

## Best Practices

1. **Large Datasets**: Use batch workflows for datasets with many species
2. **Resource Management**: Adjust workers and batch size based on system resources
3. **Error Handling**: Always use `--save-failed` to track failures for retry
4. **MPS Issues**: Use `--cpu` flag if experiencing crashes on Apple Silicon
5. **Rate Limiting**: Use `--delay` to be respectful to image servers
6. **Monitoring**: Watch progress bars and logs for errors

## Troubleshooting

### Batch Download Issues

**SSL Errors:**
```bash
# Reduce workers and add delay
python workflows/batch/batch_download.py ... --workers 2 --delay 2
```

**Timeout Errors:**
```bash
# Use sequential processing with retries
python workflows/batch/batch_download.py ... --workers 1 --max-retries 5
```

### Batch Embeddings Issues

**MPS Crashes (Python 3.13):**
```bash
# Force CPU mode
python workflows/batch/batch_embeddings.py ... --cpu
```

**Out of Memory:**
```bash
# Reduce batch size
python workflows/batch/batch_embeddings.py ... --batch-size 16
```

**Multiprocessing Errors:**
- Already fixed: Scripts use sequential processing to avoid GPU context issues
- If you still see semaphore leaks, they're harmless and will be cleaned up

## Migration Notes

These workflows were migrated from `scripts/images/batch_*.py` to use the plantnet package structure. The original scripts are preserved in the repository for reference but should not be used for new work.

**Key Changes:**
- Updated imports to use `plantnet.*` package
- Uses centralized path management from `plantnet.utils.paths`
- Maintained backward compatibility with fallback imports
- Improved error messages and documentation
