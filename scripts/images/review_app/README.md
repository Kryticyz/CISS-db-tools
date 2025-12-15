# Duplicate Review Application - Refactored Architecture

This directory contains the refactored, modular version of the duplicate image review tool.

## Overview

The original `review_duplicates.py` was a ~3300 line monolithic script. This refactored version splits it into focused, maintainable modules:

```
review_app/
├── __init__.py                 # Package initialization
├── core/                       # Core business logic
│   ├── __init__.py            # Exports public API
│   ├── api.py                 # DetectionAPI with cache management
│   ├── detection.py           # Duplicate/CNN detection logic
│   └── storage.py             # FAISS embedding store
└── server/                     # HTTP server components
    ├── __init__.py            # Exports server classes
    ├── handlers.py            # HTTP request handlers
    └── html_template.py       # HTML/CSS/JS generation
```

## Architecture

### Core Module (`core/`)

**`storage.py`** - FAISS Embedding Store
- `FAISSEmbeddingStore`: Fast similarity search using pre-computed embeddings
- `init_faiss_store()`: Initialize FAISS store from disk

**`detection.py`** - Detection Logic
- `get_species_list()`: List available species
- `get_species_duplicates()`: Find perceptual hash duplicates
- `get_species_cnn_similarity()`: Find CNN-based similar images
- `get_all_species_duplicates()`: Batch process all species
- `delete_files()`: Safe file deletion with validation

**`api.py`** - Detection API Wrapper
- `DetectionAPI`: Manages hash/CNN caches and coordinates detection functions
- Provides clean interface for HTTP handlers
- Handles cache lifecycle

### Server Module (`server/`)

**`handlers.py`** - HTTP Request Handlers
- `DuplicateReviewHandler`: Base HTTP handler
- `create_handler_class()`: Factory for dependency injection
- Routes for species list, duplicates, CNN similarity, images, deletion

**`html_template.py`** - UI Template
- `generate_html_page()`: Full HTML/CSS/JS for web interface
- Dark theme with interactive controls
- Client-side duplicate re-grouping
- LocalStorage caching

## Usage

### As a Standalone Application

```bash
# Run the refactored version
python review_duplicates_v2.py /path/to/by_species
python review_duplicates_v2.py /path/to/by_species --port 8080
```

### As a Library

```python
from review_app.core import DetectionAPI, init_faiss_store
from pathlib import Path

# Initialize
base_dir = Path("data/images/by_species")
faiss_store = init_faiss_store(Path("data/databases/embeddings"))
api = DetectionAPI(faiss_store=faiss_store)

# Get duplicates
result = api.get_species_duplicates(
    base_dir, "Acacia_dealbata", hash_size=16, hamming_threshold=5
)

# Get CNN similarity
result = api.get_species_cnn_similarity(
    base_dir, "Acacia_dealbata", similarity_threshold=0.85
)

# Cache management
stats = api.get_cache_stats()
api.clear_hash_cache()
```

## Benefits of Refactoring

### Maintainability
- **Single Responsibility**: Each module has a clear, focused purpose
- **Easier to Navigate**: ~200-400 lines per file vs 3300 in one file
- **Easier to Test**: Can test individual modules in isolation

### Reusability
- **Library Usage**: Core logic can be imported by other scripts
- **Dependency Injection**: Easy to swap implementations (e.g., different storage backends)
- **Clean API**: `DetectionAPI` provides a simple, consistent interface

### Extensibility
- **New Detection Types**: Add new detection modules without touching existing code
- **New Storage Backends**: Swap FAISS for alternatives (e.g., Annoy, HNSW)
- **New UI Frameworks**: Replace HTML template with React/Vue/etc

### Performance
- **Explicit Caching**: `DetectionAPI` manages caches transparently
- **Dependency Control**: Only import what you need
- **Future: Async Support**: Modular structure makes async refactoring easier

## Migration Guide

### From Original to Refactored

The refactored version maintains **full API compatibility** with the original:

| Original                     | Refactored                     |
|------------------------------|--------------------------------|
| `python review_duplicates.py` | `python review_duplicates_v2.py` |
| Same command-line arguments  | Same command-line arguments    |
| Same web UI                  | Same web UI (simplified)       |
| Same API endpoints           | Same API endpoints             |

### Importing as Library

**Before (not possible):**
```python
# Original was not importable as a library
```

**After:**
```python
from review_app.core import DetectionAPI, init_faiss_store

api = DetectionAPI()
result = api.get_species_duplicates(...)
```

## Testing

Run basic import tests:

```bash
# Test core imports
python -c "from review_app.core import DetectionAPI, init_faiss_store; print('✓ Core imports OK')"

# Test server imports  
python -c "from review_app.server import create_handler_class; print('✓ Server imports OK')"

# Test detection logic
python -c "from review_app.core.detection import get_species_list; print('✓ Detection imports OK')"
```

## Future Improvements

### Short-term
- [ ] Extract HTML/CSS/JS to separate static files
- [ ] Add unit tests for each module
- [ ] Add type hints throughout
- [ ] Add logging framework

### Medium-term
- [ ] Replace inline HTML with template engine (Jinja2)
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Add configuration file support (YAML/TOML)
- [ ] Add CLI progress bars for batch operations

### Long-term
- [ ] Async/await for concurrent operations
- [ ] WebSocket support for real-time updates
- [ ] Database backend for persistent state
- [ ] REST API mode (JSON-only, no HTML)
- [ ] Docker containerization

## File Size Comparison

| File                          | Lines | Purpose                        |
|-------------------------------|-------|--------------------------------|
| **Original**                  |       |                                |
| `review_duplicates.py`        | 3,320 | Everything in one file         |
| **Refactored**                |       |                                |
| `core/storage.py`             | 145   | FAISS store                    |
| `core/detection.py`           | 360   | Detection logic                |
| `core/api.py`                 | 95    | API wrapper                    |
| `server/handlers.py`          | 165   | HTTP handlers                  |
| `server/html_template.py`     | 240   | HTML template (simplified)     |
| `review_duplicates_v2.py`     | 125   | Main entry point               |
| **Total**                     | 1,130 | **66% reduction in complexity**|

## License

Same as parent project.
