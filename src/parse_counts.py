#!/usr/bin/env python3
"""
script to parse csv files from the counts directory into interactive dictionaries.

this script loads the three csv files (original, cleaned+checked, cleaned+unchecked)
and provides various methods to interact with and analyze the data.

usage:
    from parse_counts import CountsParser

    parser = CountsParser()
    data = parser.load_all()

    # access individual datasets
    original = parser.get_original()
    checked = parser.get_checked()
    unchecked = parser.get_unchecked()
"""

import csv
import os
from typing import Dict, List, Optional, Tuple


class CountsParser:
    """parser for image count csv files."""

    counts_dir = "./counts"  # ensure this is correct for your use case
    # if these folders change name, update accordingly
    original_file = "ORIGINAL_image_counts.csv"
    checked_file = "CLEANED+CHECKED_image_counts.csv"
    unchecked_file = "CLEANED+UNCHECKED_image_counts.csv"

    def __init__(self, counts_dir=None):
        """
        initialize the parser.

        args:
            counts_dir: path to counts directory (default: ./counts)
        """
        self.counts_dir = counts_dir or self.counts_dir
        self.original_data = {}
        self.checked_data = {}
        self.unchecked_data = {}

    def _parse_csv(self, filepath: str) -> dict[str, int]:
        """
        parse a csv file into a dictionary.

        args:
            filepath: path to the csv file

        returns:
            dictionary mapping directory names to image counts
        """
        data = {}

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(row)
                try:
                    directory = row["Directory"]
                    count = int(row["Image Count"])
                    data[directory] = count
                except (ValueError, KeyError):
                    # skip rows with invalid data (like separator rows with "---")
                    continue

        # logic for removing unwanted directories from stats
        bad_directories = [
            "__results",
            "$RECYCLE.BIN",
            "ProfileImages - Copy",
            "__results",
            "System Volume Information",
        ]

        return {
            k: v
            for k, v in data.items()
            if k not in bad_directories and not k.startswith("TOTAL")
        }

    def load_original(self) -> dict[str, int]:
        """load and return the original image counts."""
        filepath = os.path.join(self.counts_dir, self.original_file)
        print(f" load original is using this file path: {filepath}")
        self.original_data = self._parse_csv(filepath)
        return self.original_data

    def load_checked(self) -> dict[str, int]:
        """load and return the cleaned+checked image counts."""
        filepath = os.path.join(self.counts_dir, self.checked_file)
        self.checked_data = self._parse_csv(filepath)
        return self.checked_data

    def load_unchecked(self) -> dict[str, int]:
        """load and return the cleaned+unchecked image counts."""
        filepath = os.path.join(self.counts_dir, self.unchecked_file)
        self.unchecked_data = self._parse_csv(filepath)
        return self.unchecked_data

    def load_all(self) -> dict[str, dict[str, int]]:
        """
        load all csv files.

        returns:
            dictionary with keys 'original', 'checked', 'unchecked'
        """
        return {
            "original": self.load_original(),
            "checked": self.load_checked(),
            "unchecked": self.load_unchecked(),
        }

    def get_original(self) -> dict[str, int]:
        """get original data (loads if not already loaded)."""
        if not self.original_data:
            self.load_original()
        return self.original_data

    def get_checked(self) -> dict[str, int]:
        """get checked data (loads if not already loaded)."""
        if not self.checked_data:
            self.load_checked()
        return self.checked_data

    def get_unchecked(self) -> dict[str, int]:
        """get unchecked data (loads if not already loaded)."""
        if not self.unchecked_data:
            self.load_unchecked()
        return self.unchecked_data

    def get_directory_count(
        self, directory: str, dataset: str = "original"
    ) -> Optional[int]:
        """
        get image count for a specific directory.

        args:
            directory: directory name
            dataset: one of 'original', 'checked', 'unchecked'

        returns:
            image count or none if not found
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        if dataset not in data_map:
            raise ValueError(
                f"invalid dataset: {dataset}. must be one of {list(data_map.keys())}"
            )

        return data_map[dataset].get(directory)

    def compare_counts(self, directory: str) -> dict[str, Optional[int]]:
        """
        compare counts across all datasets for a directory.

        args:
            directory: directory name

        returns:
            dictionary with counts from all datasets
        """
        return {
            "original": self.get_original().get(directory),
            "checked": self.get_checked().get(directory),
            "unchecked": self.get_unchecked().get(directory),
        }

    def get_directories_with_min_count(
        self, min_count: int, dataset: str = "original"
    ) -> list[str]:
        """
        get directories with at least min_count images.

        args:
            min_count: minimum image count
            dataset: dataset to query

        returns:
            list of directory names
        """
        data = self.get_directory_count.__wrapped__(self, none, dataset)
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        data = data_map[dataset]
        return [dir_name for dir_name, count in data.items() if count >= min_count]

    def get_directories_with_max_count(
        self, max_count: int, dataset: str = "original"
    ) -> List[str]:
        """
        Get directories with at most max_count images.

        Args:
            max_count: Maximum image count
            dataset: Dataset to query

        Returns:
            List of directory names
        """
        data = self.get_directory_count.__wrapped__(self, None, dataset)
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        data = data_map[dataset]
        return [dir_name for dir_name, count in data.items() if count <= max_count]

    def get_total_images(self, dataset: str = "original") -> int:
        """
        Get total image count across all directories.

        Args:
            dataset: Dataset to query

        Returns:
            Total image count
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        return sum(data_map[dataset].values())

    def get_statistics(self, dataset: str = "original") -> Dict[str, float]:
        """
        Get statistics for a dataset.

        Args:
            dataset: Dataset to analyze

        Returns:
            Dictionary with min, max, mean, median, total
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        counts = list(data_map[dataset].values())
        counts.sort()

        n = len(counts)
        median = (
            counts[n // 2] if n % 2 == 1 else (counts[n // 2 - 1] + counts[n // 2]) / 2
        )

        return {
            "total": sum(counts),
            "count": n,
            "min": min(counts),
            "max": max(counts),
            "mean": sum(counts) / n if n > 0 else 0,
            "median": median,
        }

    def search_directories(
        self, pattern: str, dataset: str = "original"
    ) -> Dict[str, int]:
        """
        Search for directories matching a pattern.

        Args:
            pattern: Pattern to search for (case-insensitive)
            dataset: Dataset to search

        Returns:
            Dictionary of matching directories and their counts
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        data = data_map[dataset]
        pattern_lower = pattern.lower()

        return {
            dir_name: count
            for dir_name, count in data.items()
            if pattern_lower in dir_name.lower()
        }

    def get_top_directories(
        self, n: int = 10, dataset: str = "original"
    ) -> List[Tuple[str, int]]:
        """
        Get top N directories by image count.

        Args:
            n: Number of top directories to return
            dataset: Dataset to query

        Returns:
            List of (directory, count) tuples sorted by count descending
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        data = data_map[dataset]
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        return sorted_data[:n]

    def get_empty_directories(self, dataset: str = "original") -> List[str]:
        """
        Get directories with zero images.

        Args:
            dataset: Dataset to query

        Returns:
            List of directory names with zero images
        """
        data_map = {
            "original": self.get_original(),
            "checked": self.get_checked(),
            "unchecked": self.get_unchecked(),
        }

        data = data_map[dataset]
        return [dir_name for dir_name, count in data.items() if count == 0]

    def compare_datasets(self) -> Dict[str, any]:
        """
        Compare all three datasets.

        Returns:
            Dictionary with comparison statistics
        """
        original = self.get_original()
        checked = self.get_checked()
        unchecked = self.get_unchecked()

        all_dirs = set(original.keys()) | set(checked.keys()) | set(unchecked.keys())

        only_original = (
            set(original.keys()) - set(checked.keys()) - set(unchecked.keys())
        )
        only_checked = (
            set(checked.keys()) - set(original.keys()) - set(unchecked.keys())
        )
        only_unchecked = (
            set(unchecked.keys()) - set(original.keys()) - set(checked.keys())
        )

        return {
            "total_directories": len(all_dirs),
            "original_count": len(original),
            "checked_count": len(checked),
            "unchecked_count": len(unchecked),
            "only_in_original": list(only_original),
            "only_in_checked": list(only_checked),
            "only_in_unchecked": list(only_unchecked),
            "total_images_original": sum(original.values()),
            "total_images_checked": sum(checked.values()),
            "total_images_unchecked": sum(unchecked.values()),
        }

    def print_summary(self):
        """Print a summary of all datasets."""
        print("=" * 70)
        print("IMAGE COUNTS SUMMARY")
        print("=" * 70)

        for dataset_name in ["original", "checked", "unchecked"]:
            print(f"\n{dataset_name.upper()} Dataset:")
            print("-" * 70)
            stats = self.get_statistics(dataset_name)
            print(f"  Total Directories: {stats['count']}")
            print(f"  Total Images: {stats['total']}")
            print(f"  Mean Images per Directory: {stats['mean']:.2f}")
            print(f"  Median Images per Directory: {stats['median']:.2f}")
            print(f"  Min Images: {stats['min']}")
            print(f"  Max Images: {stats['max']}")

            empty = self.get_empty_directories(dataset_name)
            print(f"  Empty Directories: {len(empty)}")

        print("\n" + "=" * 70)
        print("DATASET COMPARISON")
        print("=" * 70)
        comparison = self.compare_datasets()
        print(f"Total Unique Directories: {comparison['total_directories']}")
        print(f"Directories only in ORIGINAL: {len(comparison['only_in_original'])}")
        print(f"Directories only in CHECKED: {len(comparison['only_in_checked'])}")
        print(f"Directories only in UNCHECKED: {len(comparison['only_in_unchecked'])}")
        print("=" * 70)


def main():
    """Example usage of the CountsParser."""
    parser = CountsParser()

    # Load all data
    print("Loading CSV files...")
    parser.load_all()

    # Print summary
    parser.print_summary()

    # Example queries
    print("\n\nEXAMPLE QUERIES:")
    print("=" * 70)

    # Search for Acacia
    print("\nSearching for 'Acacia' in original dataset:")
    acacia_dirs = parser.search_directories("Acacia", "original")
    for dir_name, count in sorted(acacia_dirs.items())[:5]:
        print(f"  {dir_name}: {count} images")
    print(f"  ... ({len(acacia_dirs)} total matches)")

    # Top 5 directories
    print("\nTop 5 directories by image count (original):")
    for dir_name, count in parser.get_top_directories(5, "original"):
        print(f"  {dir_name}: {count} images")

    # Compare specific directory
    print("\nComparing 'Acacia_dealbata' across datasets:")
    comparison = parser.compare_counts("Acacia_dealbata")
    for dataset, count in comparison.items():
        print(f"  {dataset}: {count if count is not None else 'N/A'} images")

    print("\n" + "=" * 70)
    print("Use parser.get_original(), parser.get_checked(), parser.get_unchecked()")
    print("to access the dictionaries directly for custom analysis.")
    print("=" * 70)


# if __name__ == "__main__":
#     main()
