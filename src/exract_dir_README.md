
## Bash Script Usage

Extract directory names from CSV files:

```bash
# Basic usage
./extract_directories.sh counts/ORIGINAL_image_counts.csv

# Save to file
./extract_directories.sh -o directories.txt counts/ORIGINAL_image_counts.csv

# Include header
./extract_directories.sh --header counts/ORIGINAL_image_counts.csv

# Show help
./extract_directories.sh --help
```
