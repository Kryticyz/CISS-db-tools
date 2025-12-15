#!/usr/bin/env python3
"""
Test script for GBIF parser functionality.

This script runs basic tests on the parse_gbif module to verify
that the parser and query methods work correctly.

Usage:
    python test_gbif.py
"""

import sys
from pathlib import Path

# Add scripts/data_processing to path to import parse_gbif
sys.path.insert(0, str(Path(__file__).parent.parent / "data_processing"))
from parse_gbif import GBIFParser


def print_test_header(test_name):
    """Print a formatted test header."""
    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print("=" * 70)


def test_loading(parser, max_rows=1000):
    """Test data loading."""
    print_test_header("Data Loading")

    print(f"Loading first {max_rows} rows from each file...")
    data = parser.load_all(max_rows=max_rows)

    print(f"✓ Multimedia records loaded: {len(data['multimedia']):,}")
    print(f"✓ Occurrence records loaded: {len(data['occurrences']):,}")

    if data["multimedia"]:
        print(
            f"✓ Sample multimedia record keys: {list(data['multimedia'][0].keys())[:5]}"
        )
    if data["occurrences"]:
        print(
            f"✓ Sample occurrence record keys: {list(data['occurrences'][0].keys())[:5]}"
        )

    return True


def test_gbif_id_lookup(parser):
    """Test GBIF ID lookup."""
    print_test_header("GBIF ID Lookup")

    occurrences = parser.get_occurrences()
    if not occurrences:
        print("✗ No occurrences loaded")
        return False

    # Get first GBIF ID
    test_id = occurrences[0]["gbifID"]
    print(f"Testing with GBIF ID: {test_id}")

    # Test occurrence lookup
    occurrence = parser.get_occurrence_by_gbif_id(test_id)
    if occurrence:
        print(f"✓ Found occurrence: {occurrence.get('scientificName')}")
    else:
        print("✗ Occurrence not found")
        return False

    # Test multimedia lookup
    images = parser.get_images_by_gbif_id(test_id)
    print(f"✓ Found {len(images)} multimedia record(s)")

    # Test complete observation
    complete = parser.get_complete_observation(test_id)
    print(f"✓ Complete observation retrieved")

    return True


def test_species_search(parser):
    """Test species search."""
    print_test_header("Species Search")

    occurrences = parser.get_occurrences()
    if not occurrences:
        print("✗ No occurrences loaded")
        return False

    # Get a species name from data
    test_species = None
    for occ in occurrences[:10]:
        species = occ.get("scientificName")
        if species and len(species.split()) >= 2:
            test_species = species.split()[0]  # Get genus
            break

    if not test_species:
        print("✗ No suitable species found for testing")
        return False

    print(f"Searching for species containing: {test_species}")
    results = parser.search_by_species(test_species)
    print(f"✓ Found {len(results)} matching observation(s)")

    if results:
        print(f"  Sample: {results[0].get('scientificName')}")

    return True


def test_country_search(parser):
    """Test country search."""
    print_test_header("Country Search")

    occurrences = parser.get_occurrences()
    if not occurrences:
        print("✗ No occurrences loaded")
        return False

    # Get a country code from data
    test_country = None
    for occ in occurrences:
        country = occ.get("countryCode")
        if country:
            test_country = country
            break

    if not test_country:
        print("✗ No country codes found in data")
        return False

    print(f"Searching for country: {test_country}")
    results = parser.search_by_country(test_country)
    print(f"✓ Found {len(results)} observation(s) in {test_country}")

    return True


def test_user_search(parser):
    """Test user search."""
    print_test_header("User Search")

    multimedia = parser.get_multimedia()
    if not multimedia:
        print("✗ No multimedia loaded")
        return False

    # Get a creator from data
    test_user = None
    for media in multimedia:
        creator = media.get("creator")
        if creator:
            # Use first word of creator name
            test_user = creator.split()[0]
            break

    if not test_user:
        print("✗ No creators found in data")
        return False

    print(f"Searching for user containing: {test_user}")
    results = parser.search_by_user(test_user)
    print(f"✓ Found {len(results)} image(s)")

    return True


def test_date_filter(parser):
    """Test date range filtering."""
    print_test_header("Date Range Filter")

    occurrences = parser.get_occurrences()
    if not occurrences:
        print("✗ No occurrences loaded")
        return False

    # Get date range from data
    dates = [occ.get("eventDate") for occ in occurrences if occ.get("eventDate")]
    if not dates:
        print("✗ No dates found in data")
        return False

    # Use first date as both start and end (should return at least 1 result)
    test_date = dates[0].split("T")[0]
    print(f"Filtering for date: {test_date}")

    results = parser.filter_by_date_range(test_date, test_date)
    print(f"✓ Found {len(results)} observation(s) on {test_date}")

    return True


def test_aggregations(parser):
    """Test aggregation methods."""
    print_test_header("Aggregation Methods")

    # Species counts
    species_counts = parser.get_species_counts()
    print(f"✓ Species counts: {len(species_counts)} unique species")

    # Country counts
    country_counts = parser.get_country_counts()
    print(f"✓ Country counts: {len(country_counts)} unique countries")

    # User counts
    user_counts = parser.get_user_counts()
    print(f"✓ User counts: {len(user_counts)} unique users")

    # Top lists
    top_species = parser.get_top_species(5)
    print(f"✓ Top 5 species retrieved")
    if top_species:
        print(f"  Most common: {top_species[0][0]} ({top_species[0][1]} obs)")

    top_countries = parser.get_top_countries(5)
    print(f"✓ Top 5 countries retrieved")
    if top_countries:
        print(f"  Most common: {top_countries[0][0]} ({top_countries[0][1]} obs)")

    top_users = parser.get_top_users(5)
    print(f"✓ Top 5 users retrieved")
    if top_users:
        print(f"  Most active: {top_users[0][0]} ({top_users[0][1]} images)")

    return True


def test_statistics(parser):
    """Test statistics method."""
    print_test_header("Statistics")

    stats = parser.get_statistics()

    print(f"✓ Total occurrences: {stats['total_occurrences']:,}")
    print(f"✓ Total multimedia records: {stats['total_multimedia_records']:,}")
    print(f"✓ Unique observations: {stats['unique_observations']:,}")
    print(f"✓ Unique species: {stats['unique_species']:,}")
    print(f"✓ Unique countries: {stats['unique_countries']:,}")
    print(f"✓ Unique users: {stats['unique_users']:,}")
    print(f"✓ Avg images per observation: {stats['avg_images_per_observation']:.2f}")
    print(f"✓ Max images per observation: {stats['max_images_per_observation']}")

    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("GBIF PARSER TEST SUITE")
    print("=" * 70)
    print("\nThis will load a subset of data and test various functionality.")
    print("Loading full dataset may take several minutes.")
    print()

    # Ask user for test size
    try:
        response = input(
            "Enter number of rows to test (default 1000, 0 for all): "
        ).strip()
        if response == "0":
            max_rows = None
            print("Loading FULL dataset...")
        elif response:
            max_rows = int(response)
        else:
            max_rows = 1000
    except (ValueError, KeyboardInterrupt):
        print("\nUsing default: 1000 rows")
        max_rows = 1000

    print()

    # Initialize parser
    parser = GBIFParser(gbif_dir="./data/raw/gbif")

    # Track test results
    tests = [
        ("Loading", lambda: test_loading(parser, max_rows)),
        ("GBIF ID Lookup", lambda: test_gbif_id_lookup(parser)),
        ("Species Search", lambda: test_species_search(parser)),
        ("Country Search", lambda: test_country_search(parser)),
        ("User Search", lambda: test_user_search(parser)),
        ("Date Filter", lambda: test_date_filter(parser)),
        ("Aggregations", lambda: test_aggregations(parser)),
        ("Statistics", lambda: test_statistics(parser)),
    ]

    results = {}

    # Run tests
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print("-" * 70)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
