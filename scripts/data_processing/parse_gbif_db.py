#!/usr/bin/env python3
"""
Script to parse GBIF export files and save to SQLite database.

This script loads multimedia.txt and occurrence.txt files and stores them
in a SQLite database for fast querying and aggregation with counts data.

Species names are normalized with underscores (e.g., "Acacia_dealbata")
to match the filesystem directory naming convention.

Usage:
    python parse_gbif_db.py --create
    python parse_gbif_db.py --create --max-rows 10000
    python parse_gbif_db.py --info
"""

import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime
from typing import Optional


class GBIFDatabaseBuilder:
    """Builder for GBIF SQLite database."""

    def __init__(
        self,
        db_path="./data/databases/plantnet_gbif.db",
        gbif_dir="./data/raw/gbif",
    ):
        """
        Initialize the database builder.

        Args:
            db_path: Path to SQLite database file
            gbif_dir: Path to GBIF data directory
        """
        self.db_path = db_path
        self.gbif_dir = gbif_dir
        self.multimedia_file = "multimedia.txt"
        self.occurrence_file = "occurrence.txt"

    def normalize_species_name(self, scientific_name: Optional[str]) -> Optional[str]:
        """
        Normalize species name to match directory naming (underscores).

        Extracts only genus and species (first two words), ignoring author names.
        Examples:
            "Acacia dealbata Link" -> "Acacia_dealbata"
            "Mercurialis annua L." -> "Mercurialis_annua"

        Args:
            scientific_name: Scientific name with spaces and possibly author

        Returns:
            Normalized name with underscores (genus_species), or None
        """
        if not scientific_name:
            return None

        # Split by spaces and take only first two words (genus and species)
        parts = scientific_name.strip().split()
        if len(parts) >= 2:
            # Take only genus and species, ignore author and other parts
            return f"{parts[0]}_{parts[1]}"
        elif len(parts) == 1:
            # Only genus, return as-is
            return parts[0]
        else:
            return None

    def create_schema(self, conn: sqlite3.Connection):
        """
        Create database schema with tables and indexes.

        Args:
            conn: SQLite connection
        """
        cursor = conn.cursor()

        print("Creating database schema...")

        # Multimedia table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS multimedia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gbifID TEXT NOT NULL,
                type TEXT,
                format TEXT,
                identifier TEXT,
                reference_url TEXT,
                title TEXT,
                description TEXT,
                source TEXT,
                audience TEXT,
                created TEXT,
                creator TEXT,
                contributor TEXT,
                publisher TEXT,
                license TEXT,
                rightsHolder TEXT
            )
        """)

        # Occurrence table (selected key fields, can expand later)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gbifID TEXT NOT NULL UNIQUE,
                scientificName TEXT,
                species_normalized TEXT,
                acceptedScientificName TEXT,
                acceptedScientificName_normalized TEXT,
                kingdom TEXT,
                phylum TEXT,
                class TEXT,
                orderName TEXT,
                family TEXT,
                genus TEXT,
                species TEXT,
                countryCode TEXT,
                stateProvince TEXT,
                locality TEXT,
                decimalLatitude REAL,
                decimalLongitude REAL,
                coordinateUncertaintyInMeters REAL,
                elevation REAL,
                eventDate TEXT,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                recordedBy TEXT,
                individualCount INTEGER,
                basisOfRecord TEXT,
                occurrenceStatus TEXT,
                license TEXT,
                reference_url TEXT,
                issue TEXT,
                mediaType TEXT
            )
        """)

        # Create indexes for fast lookups
        print("Creating indexes...")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_multimedia_gbifID ON multimedia(gbifID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_multimedia_creator ON multimedia(creator)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_gbifID ON occurrences(gbifID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_scientificName ON occurrences(scientificName)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_species_normalized ON occurrences(species_normalized)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_acceptedScientificName_normalized ON occurrences(acceptedScientificName_normalized)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_countryCode ON occurrences(countryCode)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_family ON occurrences(family)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_genus ON occurrences(genus)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_occurrences_year ON occurrences(year)"
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

    def load_multimedia(self, conn: sqlite3.Connection, max_rows: Optional[int] = None):
        """
        Load multimedia.txt into database.

        Args:
            conn: SQLite connection
            max_rows: Maximum rows to load (None = all)
        """
        filepath = os.path.join(self.gbif_dir, self.multimedia_file)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        print(f"\nLoading {self.multimedia_file}...")

        cursor = conn.cursor()
        cursor.execute("DELETE FROM multimedia")  # Clear existing data

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            batch = []
            batch_size = 1000

            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break

                batch.append(
                    (
                        row.get("gbifID"),
                        row.get("type"),
                        row.get("format"),
                        row.get("identifier"),
                        row.get("references"),  # Read from 'references' column in file
                        row.get("title"),
                        row.get("description"),
                        row.get("source"),
                        row.get("audience"),
                        row.get("created"),
                        row.get("creator"),
                        row.get("contributor"),
                        row.get("publisher"),
                        row.get("license"),
                        row.get("rightsHolder"),
                    )
                )

                if len(batch) >= batch_size:
                    cursor.executemany(
                        """
                        INSERT INTO multimedia (
                            gbifID, type, format, identifier, reference_url,
                            title, description, source, audience, created,
                            creator, contributor, publisher, license, rightsHolder
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        batch,
                    )
                    conn.commit()
                    batch = []
                    print(f"  Loaded {i + 1:,} rows...", end="\r")

            # Insert remaining rows
            if batch:
                cursor.executemany(
                    """
                        INSERT INTO multimedia (
                            gbifID, type, format, identifier, reference_url,
                            title, description, source, audience, created,
                            creator, contributor, publisher, license, rightsHolder
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )
                conn.commit()

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM multimedia")
        count = cursor.fetchone()[0]
        print(f"✓ Loaded {count:,} multimedia records" + " " * 20)

    def load_occurrences(
        self, conn: sqlite3.Connection, max_rows: Optional[int] = None
    ):
        """
        Load occurrence.txt into database.

        Args:
            conn: SQLite connection
            max_rows: Maximum rows to load (None = all)
        """
        filepath = os.path.join(self.gbif_dir, self.occurrence_file)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        print(f"\nLoading {self.occurrence_file}...")

        cursor = conn.cursor()
        cursor.execute("DELETE FROM occurrences")  # Clear existing data

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            batch = []
            batch_size = 1000

            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break

                scientific_name = row.get("scientificName")
                accepted_name = row.get("acceptedScientificName")

                # Normalize species names (spaces to underscores)
                species_normalized = self.normalize_species_name(scientific_name)
                accepted_normalized = self.normalize_species_name(accepted_name)

                # Parse numeric fields
                try:
                    lat = (
                        float(row.get("decimalLatitude"))
                        if row.get("decimalLatitude")
                        else None
                    )
                except (ValueError, TypeError):
                    lat = None

                try:
                    lon = (
                        float(row.get("decimalLongitude"))
                        if row.get("decimalLongitude")
                        else None
                    )
                except (ValueError, TypeError):
                    lon = None

                try:
                    coord_unc = (
                        float(row.get("coordinateUncertaintyInMeters"))
                        if row.get("coordinateUncertaintyInMeters")
                        else None
                    )
                except (ValueError, TypeError):
                    coord_unc = None

                try:
                    elev = float(row.get("elevation")) if row.get("elevation") else None
                except (ValueError, TypeError):
                    elev = None

                try:
                    year = int(row.get("year")) if row.get("year") else None
                except (ValueError, TypeError):
                    year = None

                try:
                    month = int(row.get("month")) if row.get("month") else None
                except (ValueError, TypeError):
                    month = None

                try:
                    day = int(row.get("day")) if row.get("day") else None
                except (ValueError, TypeError):
                    day = None

                try:
                    ind_count = (
                        int(row.get("individualCount"))
                        if row.get("individualCount")
                        else None
                    )
                except (ValueError, TypeError):
                    ind_count = None

                batch.append(
                    (
                        row.get("gbifID"),
                        scientific_name,
                        species_normalized,
                        accepted_name,
                        accepted_normalized,
                        row.get("kingdom"),
                        row.get("phylum"),
                        row.get("class"),
                        row.get(
                            "order"
                        ),  # Note: 'order' is a reserved word, stored as orderName
                        row.get("family"),
                        row.get("genus"),
                        row.get("species"),
                        row.get("countryCode"),
                        row.get("stateProvince"),
                        row.get("locality"),
                        lat,
                        lon,
                        coord_unc,
                        elev,
                        row.get("eventDate"),
                        year,
                        month,
                        day,
                        row.get("recordedBy"),
                        ind_count,
                        row.get("basisOfRecord"),
                        row.get("occurrenceStatus"),
                        row.get("license"),
                        row.get("references"),
                        row.get("issue"),
                        row.get("mediaType"),
                    )
                )

                if len(batch) >= batch_size:
                    cursor.executemany(
                        """
                        INSERT INTO occurrences (
                            gbifID, scientificName, species_normalized,
                            acceptedScientificName, acceptedScientificName_normalized,
                            kingdom, phylum, class, orderName, family, genus, species,
                            countryCode, stateProvince, locality,
                            decimalLatitude, decimalLongitude, coordinateUncertaintyInMeters,
                            elevation, eventDate, year, month, day,
                            recordedBy, individualCount, basisOfRecord, occurrenceStatus,
                            license, reference_url, issue, mediaType
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        batch,
                    )
                    conn.commit()
                    batch = []
                    print(f"  Loaded {i + 1:,} rows...", end="\r")

            # Insert remaining rows
            if batch:
                cursor.executemany(
                    """
                        INSERT INTO occurrences (
                            gbifID, scientificName, species_normalized,
                            acceptedScientificName, acceptedScientificName_normalized,
                            kingdom, phylum, class, orderName, family, genus, species,
                            countryCode, stateProvince, locality,
                            decimalLatitude, decimalLongitude, coordinateUncertaintyInMeters,
                            elevation, eventDate, year, month, day,
                            recordedBy, individualCount, basisOfRecord, occurrenceStatus,
                            license, reference_url, issue, mediaType
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )
                conn.commit()

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM occurrences")
        count = cursor.fetchone()[0]
        print(f"✓ Loaded {count:,} occurrence records" + " " * 20)

    def save_metadata(self, conn: sqlite3.Connection, max_rows: Optional[int] = None):
        """
        Save metadata about the database.

        Args:
            conn: SQLite connection
            max_rows: Max rows that were loaded (for metadata)
        """
        cursor = conn.cursor()

        metadata = {
            "created_at": datetime.now().isoformat(),
            "source_dir": self.gbif_dir,
            "multimedia_file": self.multimedia_file,
            "occurrence_file": self.occurrence_file,
            "max_rows": str(max_rows) if max_rows else "all",
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

    def create_database(self, max_rows: Optional[int] = None):
        """
        Create SQLite database from GBIF files.

        Args:
            max_rows: Maximum rows to load per file (None = all)
        """
        print("=" * 70)
        print("GBIF DATABASE BUILDER")
        print("=" * 70)
        print(f"Database: {self.db_path}")
        print(f"Source: {self.gbif_dir}")
        if max_rows:
            print(f"Limit: {max_rows:,} rows per file")
        else:
            print("Limit: Loading all rows (this may take several minutes)")
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
            self.load_multimedia(conn, max_rows)
            self.load_occurrences(conn, max_rows)

            # Save metadata
            self.save_metadata(conn, max_rows)

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
            cursor.execute("SELECT COUNT(*) FROM multimedia")
            multi_count = cursor.fetchone()[0]
            print(f"  Multimedia records: {multi_count:,}")

            cursor.execute("SELECT COUNT(*) FROM occurrences")
            occ_count = cursor.fetchone()[0]
            print(f"  Occurrence records: {occ_count:,}")

            # Species stats
            cursor.execute(
                "SELECT COUNT(DISTINCT species_normalized) FROM occurrences WHERE species_normalized IS NOT NULL"
            )
            species_count = cursor.fetchone()[0]
            print(f"  Unique species (normalized): {species_count:,}")

            cursor.execute(
                "SELECT COUNT(DISTINCT countryCode) FROM occurrences WHERE countryCode IS NOT NULL"
            )
            country_count = cursor.fetchone()[0]
            print(f"  Unique countries: {country_count:,}")

            cursor.execute(
                "SELECT COUNT(DISTINCT creator) FROM multimedia WHERE creator IS NOT NULL"
            )
            creator_count = cursor.fetchone()[0]
            print(f"  Unique contributors: {creator_count:,}")

            # Sample data
            print("\nSample Records:")
            cursor.execute(
                """
                SELECT scientificName, species_normalized, countryCode
                FROM occurrences
                WHERE species_normalized IS NOT NULL
                LIMIT 5
            """
            )
            print("  Scientific Name → Normalized:")
            for sci_name, norm_name, country in cursor.fetchall():
                print(f"    {sci_name} → {norm_name} ({country})")

            print("=" * 70)

        finally:
            if should_close:
                conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build SQLite database from GBIF PlantNet data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create database with all data (takes 2-5 minutes)
  %(prog)s --create

  # Create database with subset for testing
  %(prog)s --create --max-rows 10000

  # Show database info
  %(prog)s --info

  # Custom paths
  %(prog)s --create --db-path ./my_gbif.db --gbif-dir ./data/gbif
        """,
    )

    parser.add_argument(
        "--create", action="store_true", help="Create database from GBIF files"
    )
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument(
        "--db-path",
        default="./data/databases/plantnet_gbif.db",
        help="Path to SQLite database (default: ./data/databases/plantnet_gbif.db)",
    )
    parser.add_argument(
        "--gbif-dir",
        default="./data/raw/gbif",
        help="Path to GBIF data directory (default: ./data/raw/gbif)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Maximum rows to load per file (for testing)",
    )

    args = parser.parse_args()

    if not args.create and not args.info:
        parser.print_help()
        return

    builder = GBIFDatabaseBuilder(db_path=args.db_path, gbif_dir=args.gbif_dir)

    try:
        if args.create:
            builder.create_database(max_rows=args.max_rows)

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
