#!/usr/bin/env python3
"""
Script to parse image count CSV files and save to SQLite database.

This script loads the three count CSV files (original, cleaned+checked,
cleaned+unchecked) and stores them in a SQLite database for fast querying
and aggregation with GBIF data.

Directory names are used as-is with underscores (e.g., "Acacia_dealbata")
to match the filesystem naming convention.

Usage:
    python parse_counts_db.py --create
    python parse_counts_db.py --info
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime
from typing import Dict, List, Optional


class CountsDatabaseBuilder:
    """Builder for image counts SQLite database."""

    def __init__(self, db_path="./plantnet_counts.db", counts_dir="./counts"):
        """
        Initialize the database builder.

        Args:
            db_path: Path to SQLite database file
            counts_dir: Path to counts directory
        """
        self.db_path = db_path
        self.counts_dir = counts_dir
        self.original_file = "ORIGINAL_image_counts.csv"
        self.checked_file = "CLEANED+CHECKED_image_counts.csv"
        self.unchecked_file = "CLEANED+UNCHECKED_image_counts.csv"

    def create_schema(self, conn: sqlite3.Connection):
        """
        Create database schema with tables and indexes.

        Args:
            conn: SQLite connection
        """
        cursor = conn.cursor()

        print("Creating database schema...")

        # Image counts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directory TEXT NOT NULL UNIQUE,
                original_count INTEGER,
                checked_count INTEGER,
                unchecked_count INTEGER,
                CONSTRAINT unique_directory UNIQUE (directory)
            )
        """)

        # Create indexes for fast lookups
        print("Creating indexes...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counts_directory ON image_counts(directory)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counts_original ON image_counts(original_count)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counts_checked ON image_counts(checked_count)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_counts_unchecked ON image_counts(unchecked_count)"
        )

        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        print("✓ Schema created")

    def parse_csv(self, filepath: str) -> Dict[str, int]:
        """
        Parse a CSV file into a dictionary.

        Args:
            filepath: Path to the CSV file

        Returns:
            Dictionary mapping directory names to image counts
        """
        data = {}

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    directory = row["Directory"]
                    count = int(row["Image Count"])
                    data[directory] = count
                except (ValueError, KeyError):
                    # Skip rows with invalid data (like separator rows with "---")
                    continue

        # Filter out unwanted directories
        bad_directories = [
            "__results",
            "$RECYCLE.BIN",
            "ProfileImages - Copy",
            "System Volume Information",
            "Magician Launcher.app",
        ]

        return {
            k: v
            for k, v in data.items()
            if k not in bad_directories and not k.startswith("TOTAL")
        }

    def load_counts(self, conn: sqlite3.Connection):
        """
        Load all count CSV files into database.

        Args:
            conn: SQLite connection
        """
        print("\nLoading image count files...")

        cursor = conn.cursor()
        cursor.execute("DELETE FROM image_counts")  # Clear existing data

        # Load all three files
        original_path = os.path.join(self.counts_dir, self.original_file)
        checked_path = os.path.join(self.counts_dir, self.checked_file)
        unchecked_path = os.path.join(self.counts_dir, self.unchecked_file)

        print(f"  Loading {self.original_file}...")
        original_data = self.parse_csv(original_path)
        print(f"    ✓ {len(original_data):,} directories")

        print(f"  Loading {self.checked_file}...")
        checked_data = self.parse_csv(checked_path)
        print(f"    ✓ {len(checked_data):,} directories")

        print(f"  Loading {self.unchecked_file}...")
        unchecked_data = self.parse_csv(unchecked_path)
        print(f"    ✓ {len(unchecked_data):,} directories")

        # Merge all directories
        all_directories = (
            set(original_data.keys())
            | set(checked_data.keys())
            | set(unchecked_data.keys())
        )

        print(f"\n  Merging data for {len(all_directories):,} unique directories...")

        # Insert data
        batch = []
        for directory in sorted(all_directories):
            batch.append(
                (
                    directory,
                    original_data.get(directory),
                    checked_data.get(directory),
                    unchecked_data.get(directory),
                )
            )

        cursor.executemany(
            """
            INSERT INTO image_counts (directory, original_count, checked_count, unchecked_count)
            VALUES (?, ?, ?, ?)
        """,
            batch,
        )
        conn.commit()

        print(f"✓ Loaded {len(batch):,} directory records")

    def save_metadata(self, conn: sqlite3.Connection):
        """
        Save metadata about the database.

        Args:
            conn: SQLite connection
        """
        cursor = conn.cursor()

        metadata = {
            "created_at": datetime.now().isoformat(),
            "source_dir": self.counts_dir,
            "original_file": self.original_file,
            "checked_file": self.checked_file,
            "unchecked_file": self.unchecked_file,
        }

        for key, value in metadata.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES (?, ?)
            """,
                (key, value),
            )

        conn.commit()

    def create_database(self):
        """Create SQLite database from count CSV files."""
        print("=" * 70)
        print("IMAGE COUNTS DATABASE BUILDER")
        print("=" * 70)
        print(f"Database: {self.db_path}")
        print(f"Source: {self.counts_dir}")
        print()

        # Remove existing database
        if os.path.exists(self.db_path):
            print(f"Removing existing database: {self.db_path}")
            os.remove(self.db_path)

        # Create new database
        conn = sqlite3.connect(self.db_path)

        try:
            # Create schema
            self.create_schema(conn)

            # Load data
            self.load_counts(conn)

            # Save metadata
            self.save_metadata(conn)

            print("\n" + "=" * 70)
            print("DATABASE CREATION COMPLETE")
            print("=" * 70)

            # Print summary
            self.print_database_info(conn)

        finally:
            conn.close()

        print(f"\n✓ Database saved to: {self.db_path}")

    def print_database_info(self, conn: sqlite3.Connection = None):
        """
        Print information about the database.

        Args:
            conn: SQLite connection (if None, opens new connection)
        """
        should_close = False
        if conn is None:
            if not os.path.exists(self.db_path):
                print(f"Database not found: {self.db_path}")
                return
            conn = sqlite3.connect(self.db_path)
            should_close = True

        try:
            cursor = conn.cursor()

            print("\n" + "=" * 70)
            print("DATABASE INFO")
            print("=" * 70)

            # File info
            if os.path.exists(self.db_path):
                size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
                print(f"Database file: {self.db_path}")
                print(f"File size: {size_mb:.2f} MB")

            # Metadata
            cursor.execute("SELECT key, value FROM metadata")
            metadata = dict(cursor.fetchall())
            if metadata:
                print("\nMetadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")

            # Table counts
            print("\nTable Statistics:")
            cursor.execute("SELECT COUNT(*) FROM image_counts")
            count = cursor.fetchone()[0]
            print(f"  Total directories: {count:,}")

            # Stats per dataset
            cursor.execute(
                "SELECT COUNT(*) FROM image_counts WHERE original_count IS NOT NULL"
            )
            orig_count = cursor.fetchone()[0]
            print(f"  Directories in original: {orig_count:,}")

            cursor.execute(
                "SELECT COUNT(*) FROM image_counts WHERE checked_count IS NOT NULL"
            )
            check_count = cursor.fetchone()[0]
            print(f"  Directories in checked: {check_count:,}")

            cursor.execute(
                "SELECT COUNT(*) FROM image_counts WHERE unchecked_count IS NOT NULL"
            )
            uncheck_count = cursor.fetchone()[0]
            print(f"  Directories in unchecked: {uncheck_count:,}")

            # Image totals
            cursor.execute("SELECT SUM(original_count) FROM image_counts")
            orig_total = cursor.fetchone()[0] or 0
            print(f"\n  Total images (original): {orig_total:,}")

            cursor.execute("SELECT SUM(checked_count) FROM image_counts")
            check_total = cursor.fetchone()[0] or 0
            print(f"  Total images (checked): {check_total:,}")

            cursor.execute("SELECT SUM(unchecked_count) FROM image_counts")
            uncheck_total = cursor.fetchone()[0] or 0
            print(f"  Total images (unchecked): {uncheck_total:,}")

            # Top directories
            print("\nTop 10 Directories (original count):")
            cursor.execute(
                """
                SELECT directory, original_count
                FROM image_counts
                WHERE original_count IS NOT NULL
                ORDER BY original_count DESC
                LIMIT 10
            """
            )
            for i, (directory, count) in enumerate(cursor.fetchall(), 1):
                print(f"  {i:2d}. {directory:<50} {count:>8,} images")

            # Sample data showing differences
            print("\nSample Directories (showing cleaning differences):")
            cursor.execute(
                """
                SELECT directory, original_count, checked_count,
                       (original_count - checked_count) as removed
                FROM image_counts
                WHERE original_count IS NOT NULL
                  AND checked_count IS NOT NULL
                  AND original_count != checked_count
                ORDER BY removed DESC
                LIMIT 5
            """
            )
            results = cursor.fetchall()
            if results:
                print(
                    f"  {'Directory':<40} {'Original':>10} {'Checked':>10} {'Removed':>10}"
                )
                print("  " + "-" * 70)
                for directory, orig, check, removed in results:
                    print(f"  {directory:<40} {orig:>10,} {check:>10,} {removed:>10,}")
            else:
                print("  No differences found")

            print("=" * 70)

        finally:
            if should_close:
                conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build SQLite database from image count CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create database from CSV files
  %(prog)s --create

  # Show database info
  %(prog)s --info

  # Custom paths
  %(prog)s --create --db-path ./my_counts.db --counts-dir ./data/counts
        """,
    )

    parser.add_argument(
        "--create", action="store_true", help="Create database from CSV files"
    )
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument(
        "--db-path",
        default="./plantnet_counts.db",
        help="Path to SQLite database (default: ./plantnet_counts.db)",
    )
    parser.add_argument(
        "--counts-dir",
        default="./counts",
        help="Path to counts directory (default: ./counts)",
    )

    args = parser.parse_args()

    if not args.create and not args.info:
        parser.print_help()
        return

    builder = CountsDatabaseBuilder(db_path=args.db_path, counts_dir=args.counts_dir)

    try:
        if args.create:
            builder.create_database()

        if args.info:
            builder.print_database_info()

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
