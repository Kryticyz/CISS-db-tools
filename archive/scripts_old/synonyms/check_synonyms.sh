#!/bin/bash

# Script to check species_synonyms_gbif.json for mismatched query and accepted names
# Outputs GBIF accepted names where they differ from query names

INPUT_FILE="../../data/processed/synonyms/species_synonyms_gbif.json"
OUTPUT_FILE="../../data/reports/mismatched_species.txt"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Install it with: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: $INPUT_FILE not found!"
    exit 1
fi

echo "Checking for species with mismatched query and accepted names..."

# Parse JSON and find mismatches, output accepted names
jq -r '.species | to_entries[] |
    select(.value.query_name != .value.gbif_accepted_name) |
    .value.gbif_accepted_name' "$INPUT_FILE" > "$OUTPUT_FILE"

# Count results
count=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')

echo "Found $count species with mismatched names"
echo "Results written to: $OUTPUT_FILE"

# Display first few results as preview
if [ "$count" -gt 0 ]; then
    echo ""
    echo "Preview (first 10):"
    head -10 "$OUTPUT_FILE"

    if [ "$count" -gt 10 ]; then
        echo "..."
        echo "(showing 10 of $count total)"
    fi
fi
