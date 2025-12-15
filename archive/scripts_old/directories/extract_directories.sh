#!/bin/bash
#
# Script to extract all "Directory" fields from a CSV file
#
# Usage: ./extract_directories.sh [OPTIONS] <path_to_csv_file>
#

# Default values
OUTPUT_FILE=""
INCLUDE_HEADER=false
DELIMITER=","
COLUMN_NAME="Directory"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] <path_to_csv_file>"
    echo ""
    echo "Options:"
    echo "  -o, --output FILE      Write output to FILE instead of stdout"
    echo "  -h, --header           Include the header in output"
    echo "  -d, --delimiter CHAR   Use CHAR as delimiter (default: comma)"
    echo "  -c, --column NAME      Extract column NAME (default: Directory)"
    echo "  --help                 Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 counts/ORIGINAL_image_counts.csv"
    echo "  $0 -o directories.txt counts/ORIGINAL_image_counts.csv"
    echo "  $0 --header counts/ORIGINAL_image_counts.csv"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--header)
            INCLUDE_HEADER=true
            shift
            ;;
        -d|--delimiter)
            DELIMITER="$2"
            shift 2
            ;;
        -c|--column)
            COLUMN_NAME="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage
            ;;
        *)
            CSV_FILE="$1"
            shift
            ;;
    esac
done

# Check if file argument is provided
if [ -z "$CSV_FILE" ]; then
    echo -e "${RED}Error: No CSV file path provided${NC}" >&2
    usage
fi

# Check if file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}Error: File '$CSV_FILE' not found${NC}" >&2
    exit 1
fi

# Check if file is readable
if [ ! -r "$CSV_FILE" ]; then
    echo -e "${RED}Error: File '$CSV_FILE' is not readable${NC}" >&2
    exit 1
fi

# Extract directories using awk for robust CSV parsing
extract_directories() {
    awk -F"$DELIMITER" -v col="$COLUMN_NAME" -v header="$INCLUDE_HEADER" '
    NR==1 {
        # Find the column index
        for (i=1; i<=NF; i++) {
            gsub(/^[ \t"]+|[ \t"]+$/, "", $i)
            if ($i == col) {
                col_idx = i
                break
            }
        }
        if (col_idx == "") {
            print "Error: Column \"" col "\" not found in CSV" > "/dev/stderr"
            exit 1
        }
        if (header == "true") {
            print col
        }
        next
    }
    {
        # Extract the column value and remove quotes
        val = $col_idx
        gsub(/^[ \t"]+|[ \t"]+$/, "", val)
        print val
    }
    ' "$CSV_FILE"
}

# Execute extraction
if [ -n "$OUTPUT_FILE" ]; then
    extract_directories > "$OUTPUT_FILE"
    if [ $? -eq 0 ]; then
        COUNT=$(wc -l < "$OUTPUT_FILE")
        echo -e "${GREEN}✓ Successfully extracted $COUNT directories to: $OUTPUT_FILE${NC}" >&2
    else
        echo -e "${RED}Error: Failed to extract directories${NC}" >&2
        exit 1
    fi
else
    extract_directories
fi
