#!/usr/bin/env python3
"""
Interactive CLI tool for querying image count CSV data.

This script provides a command-line interface for querying and analyzing
the image count data from the counts directory.

Usage:
    python query_counts.py --help
    python query_counts.py --summary
    python query_counts.py --search "acacia"
    python query_counts.py --compare "Acacia_dealbata"
    python query_counts.py --top 10
    python query_counts.py --stats original
"""

import argparse
import sys

from parse_counts import CountsParser


def print_header(text, char="="):
    """Print a formatted header."""
    width = 70
    print()
    print(char * width)
    print(text.center(width))
    print(char * width)


def print_subheader(text, char="-"):
    """Print a formatted subheader."""
    width = 70
    print()
    print(text)
    print(char * len(text))


def format_number(num):
    """Format number with commas."""
    return f"{num:,}"


def cmd_summary(parser):
    """Display summary of all datasets."""
    parser.print_summary()


def cmd_search(parser, pattern, dataset, names_only=False):
    """Search for directories matching a pattern."""
    results = parser.search_directories(pattern, dataset)

    if not results:
        if not names_only:
            print(f"\nNo directories found matching '{pattern}' in {dataset} dataset")
        return

    # Sort by count descending
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

    if names_only:
        for name, _ in sorted_results:
            print(name)
        return

    print_header(f"SEARCH RESULTS: '{pattern}'")
    print(f"\nFound {len(results)} matching directories in {dataset} dataset:")
    print()

    for i, (name, count) in enumerate(sorted_results, 1):
        print(f"  {i:3d}. {name:<50} {format_number(count):>10} images")

    print()
    print(
        f"Total images in matching directories: {format_number(sum(results.values()))}"
    )


def cmd_compare(parser, directory):
    """Compare a directory across all datasets."""
    print_header(f"COMPARISON: {directory}")

    comparison = parser.compare_counts(directory)

    if all(v is None for v in comparison.values()):
        print(f"\nDirectory '{directory}' not found in any dataset")
        return

    print()
    print(f"{'Dataset':<20} {'Count':>15} {'Status'}")
    print("-" * 50)

    for dataset_name, count in comparison.items():
        if count is not None:
            status = "✓ Found"
            count_str = format_number(count)
        else:
            status = "✗ Not found"
            count_str = "N/A"

        print(f"{dataset_name.capitalize():<20} {count_str:>15} {status}")

    # Calculate differences
    orig = comparison.get("original")
    check = comparison.get("checked")
    uncheck = comparison.get("unchecked")

    if orig and check:
        diff = orig - check
        pct = (diff / orig * 100) if orig > 0 else 0
        print()
        print(f"Removed in checking: {format_number(diff)} images ({pct:.1f}%)")


def cmd_top(parser, n, dataset, names_only=False):
    """Show top N directories."""
    top = parser.get_top_directories(n, dataset)

    if names_only:
        for name, _ in top:
            print(name)
        return

    print_header(f"TOP {n} DIRECTORIES - {dataset.upper()}")

    print()
    print(f"{'Rank':<6} {'Directory':<45} {'Count':>15}")
    print("-" * 70)

    for i, (name, count) in enumerate(top, 1):
        print(f"{i:<6} {name:<45} {format_number(count):>15}")


def cmd_stats(parser, dataset):
    """Show statistics for a dataset."""
    print_header(f"STATISTICS - {dataset.upper()}")

    stats = parser.get_statistics(dataset)

    print()
    print(f"{'Metric':<30} {'Value':>20}")
    print("-" * 52)
    print(f"{'Total Directories':<30} {format_number(stats['count']):>20}")
    print(f"{'Total Images':<30} {format_number(stats['total']):>20}")
    print(f"{'Mean Images/Directory':<30} {stats['mean']:>20,.2f}")
    print(f"{'Median Images/Directory':<30} {stats['median']:>20,.2f}")
    print(f"{'Minimum Images':<30} {format_number(stats['min']):>20}")
    print(f"{'Maximum Images':<30} {format_number(stats['max']):>20}")

    # Additional statistics
    empty = parser.get_empty_directories(dataset)
    print(f"{'Empty Directories':<30} {format_number(len(empty)):>20}")


def cmd_list(parser, dataset, min_count, max_count, names_only=False):
    """List directories with optional filtering."""
    data = {
        "original": parser.get_original(),
        "checked": parser.get_checked(),
        "unchecked": parser.get_unchecked(),
    }[dataset]

    # Apply filters
    filtered = {
        k: v
        for k, v in data.items()
        if (min_count is None or v >= min_count)
        and (max_count is None or v <= max_count)
    }

    if not filtered:
        if not names_only:
            print("\nNo directories match the specified filters")
        return

    # Sort by name
    if names_only:
        for name in sorted(filtered.keys()):
            print(name)
        return

    print_header(f"DIRECTORY LIST - {dataset.upper()}")

    print()
    if min_count or max_count:
        filter_text = []
        if min_count:
            filter_text.append(f"min={min_count}")
        if max_count:
            filter_text.append(f"max={max_count}")
        print(f"Filters: {', '.join(filter_text)}")
        print()

    print(f"Found {len(filtered)} directories:")
    print()

    for name, count in sorted(filtered.items()):
        print(f"  {name:<50} {format_number(count):>10}")

    print()
    print(f"Total images: {format_number(sum(filtered.values()))}")


def cmd_info(parser, directory):
    """Show detailed information about a directory."""
    print_header(f"DIRECTORY INFO: {directory}")

    comparison = parser.compare_counts(directory)

    if all(v is None for v in comparison.values()):
        print(f"\nDirectory '{directory}' not found in any dataset")
        return

    print()

    # Basic info
    for dataset_name, count in comparison.items():
        if count is not None:
            print(f"{dataset_name.capitalize()} Dataset: {format_number(count)} images")

    # Presence in datasets
    print()
    datasets_present = [k for k, v in comparison.items() if v is not None]
    print(f"Present in: {', '.join(datasets_present)}")

    # Rankings
    print()
    for dataset_name in ["original", "checked", "unchecked"]:
        if comparison[dataset_name] is not None:
            data = {
                "original": parser.get_original(),
                "checked": parser.get_checked(),
                "unchecked": parser.get_unchecked(),
            }[dataset_name]

            sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
            rank = next(
                i for i, (name, _) in enumerate(sorted_data, 1) if name == directory
            )

            print(f"Rank in {dataset_name}: {rank} of {len(data)}")


def cmd_compare_datasets(parser):
    """Compare all datasets."""
    print_header("DATASET COMPARISON")

    comparison = parser.compare_datasets()

    print()
    print(f"{'Metric':<40} {'Value':>20}")
    print("-" * 62)
    print(
        f"{'Total Unique Directories':<40} {format_number(comparison['total_directories']):>20}"
    )
    print(
        f"{'Directories in ORIGINAL':<40} {format_number(comparison['original_count']):>20}"
    )
    print(
        f"{'Directories in CHECKED':<40} {format_number(comparison['checked_count']):>20}"
    )
    print(
        f"{'Directories in UNCHECKED':<40} {format_number(comparison['unchecked_count']):>20}"
    )
    print()
    print(
        f"{'Total Images in ORIGINAL':<40} {format_number(comparison['total_images_original']):>20}"
    )
    print(
        f"{'Total Images in CHECKED':<40} {format_number(comparison['total_images_checked']):>20}"
    )
    print(
        f"{'Total Images in UNCHECKED':<40} {format_number(comparison['total_images_unchecked']):>20}"
    )
    print()
    print(
        f"{'Only in ORIGINAL':<40} {format_number(len(comparison['only_in_original'])):>20}"
    )
    print(
        f"{'Only in CHECKED':<40} {format_number(len(comparison['only_in_checked'])):>20}"
    )
    print(
        f"{'Only in UNCHECKED':<40} {format_number(len(comparison['only_in_unchecked'])):>20}"
    )


def cmd_empty(parser, dataset, names_only=False):
    """List empty directories."""
    empty = parser.get_empty_directories(dataset)

    if not empty:
        if not names_only:
            print(f"\nNo empty directories in {dataset} dataset")
        return

    if names_only:
        for name in sorted(empty):
            print(name)
        return

    print_header(f"EMPTY DIRECTORIES - {dataset.upper()}")

    print()
    print(f"Found {len(empty)} empty directories:")
    print()

    for name in sorted(empty):
        print(f"  {name}")


def main():
    """Main CLI entry point."""
    parser_obj = argparse.ArgumentParser(
        description="Query and analyze image count CSV data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --summary
  %(prog)s --search "acacia" --dataset original
  %(prog)s --compare "Acacia_dealbata"
  %(prog)s --top 10 --dataset checked
  %(prog)s --stats original
  %(prog)s --list --min-count 1000 --dataset original
  %(prog)s --info "Acacia_dealbata"
  %(prog)s --compare-datasets
  %(prog)s --empty --dataset original
        """,
    )

    # Commands
    parser_obj.add_argument(
        "--summary", action="store_true", help="Display summary of all datasets"
    )
    parser_obj.add_argument(
        "--search", metavar="PATTERN", help="Search for directories matching pattern"
    )
    parser_obj.add_argument(
        "--compare", metavar="DIRECTORY", help="Compare a directory across all datasets"
    )
    parser_obj.add_argument(
        "--top", type=int, metavar="N", help="Show top N directories by count"
    )
    parser_obj.add_argument(
        "--stats",
        metavar="DATASET",
        choices=["original", "checked", "unchecked"],
        help="Show statistics for dataset (original, checked, unchecked)",
    )
    parser_obj.add_argument(
        "--list", action="store_true", help="List all directories with optional filters"
    )
    parser_obj.add_argument(
        "--info",
        metavar="DIRECTORY",
        help="Show detailed information about a directory",
    )
    parser_obj.add_argument(
        "--compare-datasets", action="store_true", help="Compare all three datasets"
    )
    parser_obj.add_argument(
        "--empty", action="store_true", help="List empty directories"
    )

    # Options
    parser_obj.add_argument(
        "--names-only",
        action="store_true",
        help="Output only directory names (one per line, no formatting)",
    )
    parser_obj.add_argument(
        "--dataset",
        choices=["original", "checked", "unchecked"],
        default="original",
        help="Dataset to query (default: original)",
    )
    parser_obj.add_argument(
        "--min-count", type=int, metavar="N", help="Minimum image count filter"
    )
    parser_obj.add_argument(
        "--max-count", type=int, metavar="N", help="Maximum image count filter"
    )
    parser_obj.add_argument(
        "--counts-dir",
        default="./counts",
        help="Path to counts directory (default: ./counts)",
    )

    args = parser_obj.parse_args()

    # Check if any command was specified
    if not any(
        [
            args.summary,
            args.search,
            args.compare,
            args.top,
            args.stats,
            args.list,
            args.info,
            args.compare_datasets,
            args.empty,
        ]
    ):
        parser_obj.print_help()
        return

    # Initialize parser
    try:
        parser = CountsParser(counts_dir=args.counts_dir)
        parser.load_all()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            f"Make sure you're in the correct directory or specify --counts-dir",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute commands
    try:
        if args.summary:
            cmd_summary(parser)

        if args.search:
            cmd_search(parser, args.search, args.dataset, args.names_only)

        if args.compare:
            cmd_compare(parser, args.compare)

        if args.top:
            cmd_top(parser, args.top, args.dataset, args.names_only)

        if args.stats:
            cmd_stats(parser, args.stats)

        if args.list:
            cmd_list(
                parser, args.dataset, args.min_count, args.max_count, args.names_only
            )

        if args.info:
            cmd_info(parser, args.info)

        if args.compare_datasets:
            cmd_compare_datasets(parser)

        if args.empty:
            cmd_empty(parser, args.dataset, args.names_only)

        if not args.names_only:
            print()  # Final newline

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
