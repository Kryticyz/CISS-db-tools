"""
Analysis and reporting command-line interfaces.

Provides CLI wrappers for generating reports and analyzing data.
"""

import argparse
import sys


def analyze_cli():
    """CLI for analysis and reporting."""
    parser = argparse.ArgumentParser(
        prog="plantnet-analyze",
        description="Generate analysis reports for species data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet-analyze --report species
  plantnet-analyze --outliers /path/to/embeddings

Note: For full functionality, use the Python scripts directly:
  python scripts/reports/generate_report_v3.py
  python scripts/images/detect_outliers.py
        """,
    )

    parser.add_argument(
        "--report",
        type=str,
        choices=["species", "quality"],
        help="Type of report to generate",
    )

    parser.add_argument(
        "--outliers",
        type=str,
        help="Path to embeddings directory for outlier detection",
    )

    args = parser.parse_args()

    if args.report:
        print(f"Generating {args.report} report...")
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/reports/generate_report_v3.py")
        sys.exit(0)

    if args.outliers:
        print(f"Detecting outliers in: {args.outliers}")
        print("\nNote: Full implementation coming soon.")
        print("For now, use: python scripts/images/detect_outliers.py")
        sys.exit(0)

    # No arguments provided
    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    analyze_cli()
