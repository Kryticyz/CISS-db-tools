"""
Main CLI entry point for PlantNet toolkit.

Provides a unified command-line interface for all PlantNet operations.
"""

import argparse
import sys

from plantnet import __version__


def main():
    """Main CLI dispatcher."""
    parser = argparse.ArgumentParser(
        prog="plantnet",
        description="PlantNet Image Mining Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  plantnet --version
  plantnet-db-query --summary
  plantnet-deduplicate /path/to/species
  plantnet-review /path/to/by_species

See 'plantnet-<command> --help' for detailed usage of each command.
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"plantnet {__version__}",
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run (use specific plantnet-<command> instead)",
    )

    args = parser.parse_args()

    if args.command:
        print(f"Unknown command: {args.command}")
        print("\nAvailable commands:")
        print("  plantnet-db-query      Query GBIF and counts databases")
        print("  plantnet-db-build      Build databases from raw data")
        print("  plantnet-deduplicate   Remove duplicate images")
        print("  plantnet-review        Visual duplicate review interface")
        print("  plantnet-download      Download species images")
        print("  plantnet-embeddings    Generate CNN embeddings")
        print("\nUse 'plantnet-<command> --help' for detailed usage.")
        sys.exit(1)

    parser.print_help()


if __name__ == "__main__":
    main()
