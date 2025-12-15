"""
GBIF Parser Module

Parses GBIF export files (multimedia.txt and occurrence.txt) into interactive data structures.

This module loads tab-delimited GBIF files and provides various methods
to interact with and analyze biodiversity observation data.

Usage:
    from plantnet.core.gbif_parser import GBIFParser

    parser = GBIFParser()
    data = parser.load_all()

    # Access individual datasets
    multimedia = parser.get_multimedia()
    occurrences = parser.get_occurrences()

    # Query data
    images = parser.get_images_by_gbif_id("2644196009")
    species_obs = parser.search_by_species("Acacia")
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from plantnet.utils.paths import GBIF_RAW_DIR


class GBIFParser:
    """Parser for GBIF multimedia and occurrence tab-delimited files."""

    def __init__(self, gbif_dir: Optional[Path] = None):
        """
        Initialize the parser.

        Args:
            gbif_dir: Path to GBIF directory (default: data/raw/gbif from paths.py)
        """
        self.gbif_dir = gbif_dir or GBIF_RAW_DIR
        self.multimedia_file = "multimedia.txt"
        self.occurrence_file = "occurrence.txt"
        self.multimedia_data = []  # List of dictionaries
        self.occurrence_data = []  # List of dictionaries
        self.multimedia_by_gbif_id = defaultdict(
            list
        )  # gbifID -> list of media records
        self.occurrence_by_gbif_id = {}  # gbifID -> occurrence record
        self.loaded = False

    def _parse_tsv(
        self, filepath: str, max_rows: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Parse a tab-delimited file into a list of dictionaries.

        Args:
            filepath: Path to the TSV file
            max_rows: Maximum number of rows to parse (None = all rows)

        Returns:
            List of dictionaries, one per row
        """
        data = []

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        print(f"Parsing {os.path.basename(filepath)}...")

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break

                # Clean up empty strings to None for consistency
                cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
                data.append(cleaned_row)

                if (i + 1) % 100000 == 0:
                    print(f"  Parsed {i + 1:,} rows...")

        print(f"  Complete: {len(data):,} rows loaded")
        return data

    def load_multimedia(self, max_rows: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load and return the multimedia data.

        Args:
            max_rows: Maximum number of rows to load (None = all)

        Returns:
            List of multimedia records
        """
        filepath = os.path.join(self.gbif_dir, self.multimedia_file)
        self.multimedia_data = self._parse_tsv(filepath, max_rows)

        # Build index by gbifID for fast lookup
        print("Building multimedia index...")
        self.multimedia_by_gbif_id.clear()
        for record in self.multimedia_data:
            gbif_id = record.get("gbifID")
            if gbif_id:
                self.multimedia_by_gbif_id[gbif_id].append(record)

        return self.multimedia_data

    def load_occurrences(self, max_rows: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load and return the occurrence data.

        Args:
            max_rows: Maximum number of rows to load (None = all)

        Returns:
            List of occurrence records
        """
        filepath = os.path.join(self.gbif_dir, self.occurrence_file)
        self.occurrence_data = self._parse_tsv(filepath, max_rows)

        # Build index by gbifID for fast lookup
        print("Building occurrence index...")
        self.occurrence_by_gbif_id.clear()
        for record in self.occurrence_data:
            gbif_id = record.get("gbifID")
            if gbif_id:
                self.occurrence_by_gbif_id[gbif_id] = record

        return self.occurrence_data

    def load_all(
        self, max_rows: Optional[int] = None
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Load all GBIF files.

        Args:
            max_rows: Maximum number of rows to load per file (None = all)

        Returns:
            Dictionary with keys 'multimedia' and 'occurrences'
        """
        multimedia = self.load_multimedia(max_rows)
        occurrences = self.load_occurrences(max_rows)
        self.loaded = True

        return {
            "multimedia": multimedia,
            "occurrences": occurrences,
        }

    def get_multimedia(self) -> List[Dict[str, str]]:
        """Get multimedia data (loads if not already loaded)."""
        if not self.multimedia_data:
            self.load_multimedia()
        return self.multimedia_data

    def get_occurrences(self) -> List[Dict[str, str]]:
        """Get occurrence data (loads if not already loaded)."""
        if not self.occurrence_data:
            self.load_occurrences()
        return self.occurrence_data

    def get_images_by_gbif_id(self, gbif_id: str) -> List[Dict[str, str]]:
        """
        Get all multimedia records for a specific GBIF ID.

        Args:
            gbif_id: The GBIF ID to search for

        Returns:
            List of multimedia records (may be empty)
        """
        if not self.multimedia_data:
            self.load_multimedia()
        return self.multimedia_by_gbif_id.get(gbif_id, [])

    def get_occurrence_by_gbif_id(self, gbif_id: str) -> Optional[Dict[str, str]]:
        """
        Get occurrence record for a specific GBIF ID.

        Args:
            gbif_id: The GBIF ID to search for

        Returns:
            Occurrence record or None if not found
        """
        if not self.occurrence_data:
            self.load_occurrences()
        return self.occurrence_by_gbif_id.get(gbif_id)

    def get_complete_observation(self, gbif_id: str) -> Dict[str, Any]:
        """
        Get complete observation data (occurrence + multimedia) for a GBIF ID.

        Args:
            gbif_id: The GBIF ID to search for

        Returns:
            Dictionary with 'occurrence' and 'multimedia' keys
        """
        return {
            "occurrence": self.get_occurrence_by_gbif_id(gbif_id),
            "multimedia": self.get_images_by_gbif_id(gbif_id),
        }

    def search_by_species(
        self, species_name: str, case_sensitive: bool = False
    ) -> List[Dict[str, str]]:
        """
        Search occurrences by species name (partial match).

        Args:
            species_name: Species name to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching occurrence records
        """
        occurrences = self.get_occurrences()

        if case_sensitive:
            return [
                occ
                for occ in occurrences
                if occ.get("scientificName") and species_name in occ["scientificName"]
            ]
        else:
            species_lower = species_name.lower()
            return [
                occ
                for occ in occurrences
                if occ.get("scientificName")
                and species_lower in occ["scientificName"].lower()
            ]

    def search_by_country(self, country_code: str) -> List[Dict[str, str]]:
        """
        Search occurrences by country code.

        Args:
            country_code: ISO country code (e.g., 'FR', 'ES', 'IT')

        Returns:
            List of matching occurrence records
        """
        occurrences = self.get_occurrences()
        return [occ for occ in occurrences if occ.get("countryCode") == country_code]

    def search_by_user(
        self, username: str, case_sensitive: bool = False
    ) -> List[Dict[str, str]]:
        """
        Search multimedia by creator/user name.

        Args:
            username: Username to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching multimedia records
        """
        multimedia = self.get_multimedia()

        if case_sensitive:
            return [
                media
                for media in multimedia
                if media.get("creator") and username in media["creator"]
            ]
        else:
            username_lower = username.lower()
            return [
                media
                for media in multimedia
                if media.get("creator") and username_lower in media["creator"].lower()
            ]

    def filter_by_date_range(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Filter occurrences by date range.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            List of occurrences within date range
        """
        occurrences = self.get_occurrences()
        results = []

        for occ in occurrences:
            event_date = occ.get("eventDate")
            if not event_date:
                continue

            # Extract just the date part (before 'T' if present)
            date_str = event_date.split("T")[0] if "T" in event_date else event_date

            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue

            results.append(occ)

        return results

    def get_species_counts(self) -> Dict[str, int]:
        """
        Count observations by species.

        Returns:
            Dictionary mapping species names to observation counts
        """
        occurrences = self.get_occurrences()
        counts = defaultdict(int)

        for occ in occurrences:
            species = occ.get("scientificName")
            if species:
                counts[species] += 1

        return dict(counts)

    def get_country_counts(self) -> Dict[str, int]:
        """
        Count observations by country.

        Returns:
            Dictionary mapping country codes to observation counts
        """
        occurrences = self.get_occurrences()
        counts = defaultdict(int)

        for occ in occurrences:
            country = occ.get("countryCode")
            if country:
                counts[country] += 1

        return dict(counts)

    def get_user_counts(self) -> Dict[str, int]:
        """
        Count images by creator/user.

        Returns:
            Dictionary mapping usernames to image counts
        """
        multimedia = self.get_multimedia()
        counts = defaultdict(int)

        for media in multimedia:
            creator = media.get("creator")
            if creator:
                counts[creator] += 1

        return dict(counts)

    def get_top_species(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get top N species by observation count.

        Args:
            n: Number of top species to return

        Returns:
            List of (species_name, count) tuples
        """
        counts = self.get_species_counts()
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:n]

    def get_top_countries(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get top N countries by observation count.

        Args:
            n: Number of top countries to return

        Returns:
            List of (country_code, count) tuples
        """
        counts = self.get_country_counts()
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:n]

    def get_top_users(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get top N users by image count.

        Args:
            n: Number of top users to return

        Returns:
            List of (username, count) tuples
        """
        counts = self.get_user_counts()
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:n]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics for the dataset.

        Returns:
            Dictionary with various statistics
        """
        multimedia = self.get_multimedia()
        occurrences = self.get_occurrences()

        # Count unique values
        unique_gbif_ids = len(self.occurrence_by_gbif_id)
        unique_species = len(self.get_species_counts())
        unique_countries = len(self.get_country_counts())
        unique_users = len(self.get_user_counts())

        # Images per observation
        images_per_obs = defaultdict(int)
        for gbif_id, media_list in self.multimedia_by_gbif_id.items():
            images_per_obs[gbif_id] = len(media_list)

        avg_images = (
            sum(images_per_obs.values()) / len(images_per_obs) if images_per_obs else 0
        )
        max_images = max(images_per_obs.values()) if images_per_obs else 0

        return {
            "total_occurrences": len(occurrences),
            "total_multimedia_records": len(multimedia),
            "unique_observations": unique_gbif_ids,
            "unique_species": unique_species,
            "unique_countries": unique_countries,
            "unique_users": unique_users,
            "avg_images_per_observation": avg_images,
            "max_images_per_observation": max_images,
        }

    def print_summary(self):
        """Print a summary of the dataset."""
        print("=" * 70)
        print("GBIF PLANTNET DATASET SUMMARY")
        print("=" * 70)

        stats = self.get_statistics()

        print("\nOVERALL STATISTICS:")
        print("-" * 70)
        print(f"  Total Occurrences: {stats['total_occurrences']:,}")
        print(f"  Total Multimedia Records: {stats['total_multimedia_records']:,}")
        print(f"  Unique Observations: {stats['unique_observations']:,}")
        print(f"  Unique Species: {stats['unique_species']:,}")
        print(f"  Unique Countries: {stats['unique_countries']:,}")
        print(f"  Unique Users/Contributors: {stats['unique_users']:,}")
        print(
            f"  Average Images per Observation: {stats['avg_images_per_observation']:.2f}"
        )
        print(
            f"  Maximum Images per Observation: {stats['max_images_per_observation']}"
        )

        print("\nTOP 10 SPECIES:")
        print("-" * 70)
        for i, (species, count) in enumerate(self.get_top_species(10), 1):
            print(f"  {i:2d}. {species:<50} {count:>8,} obs")

        print("\nTOP 10 COUNTRIES:")
        print("-" * 70)
        for i, (country, count) in enumerate(self.get_top_countries(10), 1):
            print(f"  {i:2d}. {country:<5} {count:>10,} observations")

        print("\nTOP 10 CONTRIBUTORS:")
        print("-" * 70)
        for i, (user, count) in enumerate(self.get_top_users(10), 1):
            print(f"  {i:2d}. {user:<50} {count:>8,} images")

        print("=" * 70)


__all__ = ["GBIFParser"]
