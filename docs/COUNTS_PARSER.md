# Image Counts CSV Parser Documentation

This directory contains Python scripts for parsing and analyzing the CSV files in the `counts` directory.

## Overview

The parser loads three CSV files containing image count data:
- `ORIGINAL_image_counts.csv` - Original dataset with all images
- `CLEANED+CHECKED_image_counts.csv` - Cleaned and manually checked dataset
- `CLEANED+UNCHECKED_image_counts.csv` - Cleaned but unchecked dataset

Each CSV contains directory names and their corresponding image counts.

## Installation

No additional dependencies required - uses only Python standard library.

```bash
# Make scripts executable (optional)
chmod +x parse_counts.py
```

## API Reference

### CountsParser Class

#### Initialization

```python
parser = CountsParser(counts_dir="./counts") # defaults to this directory, can use this to override if your csv are somewhere else
```

Parameters:
- `counts_dir` (str, optional): Path to counts directory. Default: "./counts"

#### Loading Data

**`load_all()`** - Load all three CSV files
```python
data = parser.load_all()
# Returns: {'original': {...}, 'checked': {...}, 'unchecked': {...}}
```

**`load_original()`** - Load original dataset only
```python
original = parser.load_original()
```

**`load_checked()`** - Load checked dataset only
```python
checked = parser.load_checked()
```

**`load_unchecked()`** - Load unchecked dataset only
```python
unchecked = parser.load_unchecked()
```

#### Accessing Data

**`get_original()`** - Get original dictionary (loads if needed)
```python
original = parser.get_original()
# Returns: dict mapping directory names to counts
```

**`get_checked()`** - Get checked dictionary (loads if needed)

**`get_unchecked()`** - Get unchecked dictionary (loads if needed)

#### Query Methods

**`get_directory_count(directory, dataset='original')`** - Get count for specific directory
```python
count = parser.get_directory_count("Acacia_dealbata", "original")
# Returns: int or None if not found
```

**`compare_counts(directory)`** - Compare counts across all datasets
```python
comparison = parser.compare_counts("Acacia_dealbata")
# Returns: {'original': 1173, 'checked': 634, 'unchecked': 667}
```

**`search_directories(pattern, dataset='original')`** - Search by pattern
```python
results = parser.search_directories("acacia", "original")
# Returns: dict of matching directories and counts
```

**`get_top_directories(n=10, dataset='original')`** - Get top N directories
```python
top = parser.get_top_directories(10, "original")
# Returns: list of (directory, count) tuples
```

**`get_directories_with_min_count(min_count, dataset='original')`** - Filter by minimum count
```python
high_count = parser.get_directories_with_min_count(1000, "original")
# Returns: list of directory names
```

**`get_empty_directories(dataset='original')`** - Get directories with zero images
```python
empty = parser.get_empty_directories("original")
# Returns: list of directory names
```

#### Statistics

**`get_statistics(dataset='original')`** - Get statistical summary
```python
stats = parser.get_statistics("original")
# Returns: {'total': int, 'count': int, 'min': int, 'max': int, 
#           'mean': float, 'median': float}
```

**`get_total_images(dataset='original')`** - Get total image count
```python
total = parser.get_total_images("original")
# Returns: int
```

**`compare_datasets()`** - Compare all three datasets
```python
comparison = parser.compare_datasets()
# Returns detailed comparison dictionary
```

**`print_summary()`** - Print formatted summary to console
```python
parser.print_summary()
```

## Usage Examples

### Basic Dictionary Access

```python
from parse_counts import CountsParser

parser = CountsParser()
original = parser.get_original()

# Check if directory exists
if "Acacia_dealbata" in original:
    print(f"Found! Count: {original['Acacia_dealbata']}")

# Iterate over all entries
for directory, count in original.items():
    print(f"{directory}: {count}")

# Get all directory names
all_dirs = list(original.keys())

# Get all counts
all_counts = list(original.values())
```

### Searching and Filtering

```python
parser = CountsParser()

# Search by pattern
acacia_dirs = parser.search_directories("acacia", "original")
print(f"Found {len(acacia_dirs)} Acacia species")

# Filter with dict comprehension
original = parser.get_original()
high_count = {k: v for k, v in original.items() if v > 1000}
medium_count = {k: v for k, v in original.items() if 500 <= v <= 1000}
low_count = {k: v for k, v in original.items() if v < 500}

# Get top directories
top_10 = parser.get_top_directories(10, "original")
for rank, (name, count) in enumerate(top_10, 1):
    print(f"{rank}. {name}: {count} images")
```

### Comparing Datasets

```python
parser = CountsParser()
original = parser.get_original()
checked = parser.get_checked()

# Find common directories
common = set(original.keys()) & set(checked.keys())

# Calculate image reduction
for dir_name in common:
    removed = original[dir_name] - checked[dir_name]
    if removed > 0:
        pct = (removed / original[dir_name]) * 100
        print(f"{dir_name}: {removed} removed ({pct:.1f}%)")

# Compare specific directory
comparison = parser.compare_counts("Acacia_dealbata")
print(comparison)  # Shows counts in all three datasets
```

### Statistical Analysis

```python
parser = CountsParser()

# Get statistics
stats = parser.get_statistics("original")
print(f"Mean: {stats['mean']:.2f}")
print(f"Median: {stats['median']:.2f}")
print(f"Total: {stats['total']}")

# Distribution analysis
original = parser.get_original()
counts = list(original.values())

ranges = {
    "0-100": sum(1 for c in counts if 0 <= c < 100),
    "100-500": sum(1 for c in counts if 100 <= c < 500),
    "500-1000": sum(1 for c in counts if 500 <= c < 1000),
    "1000+": sum(1 for c in counts if c >= 1000),
}

for range_name, count in ranges.items():
    print(f"{range_name}: {count} directories")
```

### Exporting Data

```python
parser = CountsParser()
original = parser.get_original()

# Export to CSV
import csv
with open('exported_counts.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Directory', 'Count'])
    for directory, count in sorted(original.items()):
        writer.writerow([directory, count])

# Export filtered data
high_count = {k: v for k, v in original.items() if v > 1000}
with open('high_count_dirs.txt', 'w') as f:
    for directory in sorted(high_count.keys()):
        f.write(f"{directory}\n")

# Export as JSON
import json
with open('counts.json', 'w') as f:
    json.dump(original, f, indent=2)
```

### Custom Analysis

```python
parser = CountsParser()
original = parser.get_original()

# Analyze by genus (first part of name)
genus_counts = {}
for dir_name, count in original.items():
    if "_" in dir_name:
        genus = dir_name.split("_")[0]
        genus_counts[genus] = genus_counts.get(genus, 0) + count

# Sort by total images per genus
sorted_genera = sorted(genus_counts.items(), key=lambda x: x[1], reverse=True)
print("Top 10 genera by total images:")
for genus, total in sorted_genera[:10]:
    print(f"  {genus}: {total}")

# Calculate percentiles
counts_sorted = sorted(original.values())
n = len(counts_sorted)
percentiles = {
    "25th": counts_sorted[n // 4],
    "50th": counts_sorted[n // 2],
    "75th": counts_sorted[3 * n // 4],
    "90th": counts_sorted[9 * n // 10],
}
print(f"Percentiles: {percentiles}")
```

## Tips and Best Practices

1. **Load Once**: Call `load_all()` once at the beginning to load all datasets
2. **Use Get Methods**: Use `get_original()` etc. instead of directly accessing attributes
3. **Dictionary Operations**: The returned dictionaries are standard Python dicts - use all normal dict operations
4. **Memory Efficient**: Dictionaries are efficient even with large datasets
5. **Error Handling**: Methods return `None` for missing directories - check before using

## Troubleshooting

**Problem**: `FileNotFoundError`
- **Solution**: Make sure you're running from the correct directory or specify `counts_dir` parameter

**Problem**: Data seems incorrect
- **Solution**: Check that CSV files haven't been modified and contain valid data

**Problem**: Slow performance
- **Solution**: Load datasets once and reuse them instead of reloading
