# Review App Architecture

## Quick Start

```bash
# Run the refactored application
cd scripts/images
python3 review_duplicates_v2.py /path/to/by_species

# Test the modules
python3 test_refactored.py
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    review_duplicates_v2.py                  │
│                     (Main Entry Point)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ├──────────────────┬──────────────────┐
                       ▼                  ▼                  ▼
         ┌─────────────────────┐  ┌─────────────┐  ┌────────────────┐
         │   review_app.core   │  │ review_app  │  │  External Deps │
         │                     │  │   .server   │  │                │
         │ ┌─────────────────┐ │  │             │  │ - deduplicate_ │
         │ │   storage.py    │ │  │ ┌─────────┐ │  │   images.py    │
         │ │ - FAISS Store   │ │  │ │handlers │ │  │ - cnn_similar- │
         │ └─────────────────┘ │  │ │  .py    │ │  │   ity.py       │
         │                     │  │ └─────────┘ │  │ - torch        │
         │ ┌─────────────────┐ │  │             │  │ - faiss        │
         │ │  detection.py   │ │  │ ┌─────────┐ │  │ - PIL          │
         │ │ - get_species   │ │  │ │  html   │ │  │ - imagehash    │
         │ │ - duplicates    │ │  │ │template │ │  └────────────────┘
         │ │ - CNN similar   │ │  │ │  .py    │ │
         │ └─────────────────┘ │  │ └─────────┘ │
         │                     │  └─────────────┘
         │ ┌─────────────────┐ │
         │ │     api.py      │ │
         │ │ - DetectionAPI  │ │
         │ │ - Cache Mgmt    │ │
         │ └─────────────────┘ │
         └─────────────────────┘
```

## Module Hierarchy

```
review_app/
│
├── core/                           # Business Logic Layer
│   ├── api.py                      # High-level API with caching
│   │   └── DetectionAPI
│   │       ├── get_species_list()
│   │       ├── get_species_duplicates()
│   │       ├── get_species_cnn_similarity()
│   │       ├── delete_files()
│   │       └── cache management
│   │
│   ├── detection.py                # Detection algorithms
│   │   ├── get_species_list()      
│   │   ├── get_species_hashes()    # Perceptual hashing
│   │   ├── get_species_duplicates() # Hash-based duplicates
│   │   ├── get_all_species_duplicates()
│   │   ├── get_species_cnn_similarity() # CNN similarity
│   │   └── delete_files()          # Safe deletion
│   │
│   └── storage.py                  # Persistence layer
│       ├── FAISSEmbeddingStore     
│       │   ├── search_species()    # Fast similarity search
│       │   └── get_status()
│       └── init_faiss_store()      # Factory function
│
└── server/                         # Presentation Layer
    ├── handlers.py                 # HTTP routing
    │   ├── DuplicateReviewHandler
    │   │   ├── do_GET()            # Handle GET requests
    │   │   ├── do_POST()           # Handle POST requests
    │   │   └── send_json/html/image()
    │   └── create_handler_class()  # Dependency injection
    │
    └── html_template.py            # UI generation
        └── generate_html_page()    # Full HTML/CSS/JS
```

## Data Flow

### Startup Sequence

```
1. review_duplicates_v2.py starts
   └─> Parses command-line arguments
   └─> Initializes FAISS store (if available)
   └─> Creates DetectionAPI instance
   └─> Creates HTTP handler class with dependencies
   └─> Starts TCP server on specified port

2. Browser connects to http://localhost:8000
   └─> Handler serves HTML template
   └─> JavaScript loads species list via /api/species
```

### Duplicate Detection Flow

```
User clicks "Analyze" button
   │
   ▼
Browser sends GET /api/duplicates/Acacia_dealbata?hash_size=16&threshold=5
   │
   ▼
handlers.py receives request
   │
   ▼
DuplicateReviewHandler.do_GET()
   │
   ▼
Calls detection_api.get_species_duplicates(...)
   │
   ▼
DetectionAPI checks hash_cache
   │
   ├─> Cache hit: Use cached hashes
   │   └─> Regroup with new threshold (client-side capable too)
   │
   └─> Cache miss: 
       └─> detection.get_species_duplicates()
           └─> Compute hashes for all images
           └─> Find duplicate groups
           └─> Store in cache
   │
   ▼
Returns JSON response with groups
   │
   ▼
Browser renders duplicate groups with images
```

### CNN Similarity Flow

```
User clicks "CNN Similarity" button
   │
   ▼
Browser sends GET /api/similarity/Acacia_dealbata?threshold=0.85
   │
   ▼
DetectionAPI.get_species_cnn_similarity()
   │
   ├─> FAISS available?
   │   └─> YES: Use pre-computed embeddings (fast!)
   │       └─> faiss_store.search_species()
   │           └─> Load embeddings from disk
   │           └─> Compare all pairs
   │           └─> Group similar images
   │
   └─> FAISS not available?
       └─> Check cnn_cache
           ├─> Cache hit: Use cached embeddings
           └─> Cache miss: 
               └─> Compute CNN embeddings (slow)
               └─> Find similar groups
               └─> Store in cache
   │
   ▼
Returns JSON response with similarity groups
```

## API Endpoints

### GET Endpoints

| Endpoint | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `/` | Main UI | - | HTML page |
| `/api/species` | List species | - | JSON array of species names |
| `/api/duplicates/{species}` | Get duplicates | `hash_size`, `threshold` | JSON with duplicate groups |
| `/api/similarity/{species}` | CNN similarity | `threshold`, `model` | JSON with similar groups |
| `/api/cnn/status` | CNN availability | - | JSON with CNN status |
| `/api/faiss/status` | FAISS availability | - | JSON with FAISS status |
| `/image/{species}/{filename}` | Serve image | - | Image file |

### POST Endpoints

| Endpoint | Purpose | Body | Returns |
|----------|---------|------|---------|
| `/api/delete` | Delete files | JSON with `files` array | JSON with deletion results |

## Caching Strategy

### Hash Cache (In-Memory)
- **Key**: `"{species_name}_{hash_size}"`
- **Value**: `Dict[Path, str]` (image path → hash string)
- **Purpose**: Avoid recomputing hashes when changing threshold
- **Lifetime**: Server process lifetime

### CNN Cache (In-Memory)
- **Key**: `"{species_name}_{model_name}"`
- **Value**: `Dict[Path, List[float]]` (image path → embedding vector)
- **Purpose**: Avoid recomputing embeddings (expensive!)
- **Lifetime**: Server process lifetime

### FAISS Store (On-Disk)
- **Location**: `data/databases/embeddings/`
- **Files**: 
  - `embeddings.index` - FAISS vector index
  - `metadata.pkl` - Image metadata
  - `metadata_full.pkl` - Full metadata with embeddings
- **Purpose**: Pre-computed embeddings for instant similarity search
- **Generation**: Run `batch_generate_embeddings.py` to create

### Client-Side Cache (LocalStorage)
- **Keys**: `plantnet_hashes_v1_{species}_{hash_size}`
- **Purpose**: Cache hashes in browser for instant re-grouping
- **Lifetime**: Persistent until cleared by user

## Security Considerations

### Path Traversal Prevention
```python
# In detection.delete_files()
full_path = (base_dir / rel_path).resolve()
if not full_path.is_relative_to(base_dir.resolve()):
    errors.append({"path": rel_path, "error": "Invalid path"})
    continue
```

### Input Validation
- Species names: URL-decoded, validated against filesystem
- File paths: Relative paths only, validated with `is_relative_to()`
- Numeric parameters: Type-checked and range-validated

### Safe Deletion
- Explicit confirmation required (not implemented in HTTP layer, delegated to UI)
- Validation before deletion
- Detailed error reporting

## Error Handling

### Module Level
- Import errors: Graceful degradation (CNN_AVAILABLE flag)
- FAISS errors: Fall back to on-demand computation
- File I/O errors: Collected and returned in results

### HTTP Level
- 404: Not found (images, endpoints)
- 500: Server errors with error message
- JSON errors: Structured error responses

### Client Level
- Network errors: Display error banner
- Invalid responses: Show error message
- Missing data: Graceful UI degradation

## Performance Characteristics

### Hash-Based Duplicates
- **First run**: O(n) to compute hashes, O(n²) to compare
- **Cached**: O(n²) to regroup (fast, client can do this)
- **Typical**: 100 images → ~1 second first run, instant thereafter

### CNN Similarity
- **With FAISS**: O(n²) with pre-computed embeddings → seconds
- **Without FAISS, cached**: O(n²) comparison → seconds  
- **Without FAISS, uncached**: O(n) CNN forward passes → minutes
- **Typical**: 100 images → 30-60 seconds first run, ~1 second with FAISS

### Memory Usage
- **Hashes**: ~32 bytes per image (hash string + overhead)
- **CNN embeddings**: ~2KB per image (512-dim float32 vector)
- **FAISS index**: ~2KB per image + index overhead
- **Typical**: 1000 images → ~2MB hashes, ~2MB embeddings

## Extension Points

### Adding New Detection Types
1. Add detection function to `core/detection.py`
2. Add API method to `core/api.py`
3. Add HTTP endpoint to `server/handlers.py`
4. Add UI controls to `server/html_template.py`

### Adding New Storage Backends
1. Create new storage class implementing same interface as `FAISSEmbeddingStore`
2. Update `init_faiss_store()` or create new factory
3. Inject into `DetectionAPI` constructor

### Adding New UI Frameworks
1. Keep existing API endpoints
2. Replace `html_template.py` with new UI framework
3. Or: Create separate endpoint that returns JSON only

## Testing Strategy

### Unit Tests (Recommended)
```python
# test_detection.py
def test_get_species_duplicates():
    api = DetectionAPI()
    result = api.get_species_duplicates(
        test_dir, "test_species", 16, 5
    )
    assert "duplicate_groups" in result
```

### Integration Tests
```python
# test_server.py
def test_api_endpoint():
    handler = create_handler_class(test_dir, api, None)
    response = requests.get("http://localhost:8000/api/species")
    assert response.status_code == 200
```

### Current Tests
See `test_refactored.py`:
- ✓ Module imports
- ✓ DetectionAPI instantiation  
- ✓ HTML generation
- ✓ Handler creation
- ✓ Species list retrieval

## Comparison: Original vs Refactored

| Aspect | Original | Refactored | Benefit |
|--------|----------|------------|---------|
| File size | 3,320 lines | 1,130 lines total | 66% smaller |
| Files | 1 | 8 modules | Better organization |
| Testability | Hard to test | Easy to test | Quality assurance |
| Reusability | Not importable | Library-ready | Code reuse |
| Maintainability | Hard to navigate | Clear structure | Development speed |
| Extensibility | Modify single file | Add new modules | Safety |
| Dependencies | Implicit | Explicit injection | Flexibility |

## Future Enhancements

See `review_app/README.md` for detailed roadmap.

Key opportunities:
- Extract HTML/CSS/JS to static files
- Add comprehensive test suite (pytest)
- Type hints + mypy validation
- Async/await for concurrency
- WebSocket for real-time updates
- Docker containerization
