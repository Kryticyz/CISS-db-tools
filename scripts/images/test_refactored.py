#!/usr/bin/env python3
"""
Basic test script for the refactored review application.

This tests that all modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from review_app.core import DetectionAPI, init_faiss_store

        print("  ✓ Core API imports OK")
    except Exception as e:
        print(f"  ✗ Core API import failed: {e}")
        return False

    try:
        from review_app.core.detection import (
            CNN_AVAILABLE,
            get_species_duplicates,
            get_species_list,
        )

        print("  ✓ Detection module imports OK")
    except Exception as e:
        print(f"  ✗ Detection module import failed: {e}")
        return False

    try:
        from review_app.core.storage import FAISSEmbeddingStore

        print("  ✓ Storage module imports OK")
    except Exception as e:
        print(f"  ✗ Storage module import failed: {e}")
        return False

    try:
        from review_app.server import create_handler_class, generate_html_page

        print("  ✓ Server module imports OK")
    except Exception as e:
        print(f"  ✗ Server module import failed: {e}")
        return False

    return True


def test_detection_api():
    """Test DetectionAPI instantiation."""
    print("\nTesting DetectionAPI...")

    try:
        from review_app.core import DetectionAPI

        api = DetectionAPI()
        print("  ✓ DetectionAPI instantiated")

        stats = api.get_cache_stats()
        print(f"  ✓ Cache stats: {stats}")

        return True
    except Exception as e:
        print(f"  ✗ DetectionAPI test failed: {e}")
        return False


def test_html_generation():
    """Test HTML generation."""
    print("\nTesting HTML generation...")

    try:
        from review_app.server import generate_html_page

        html = generate_html_page()

        if not html:
            print("  ✗ HTML generation returned empty string")
            return False

        if not html.startswith("<!DOCTYPE html>"):
            print("  ✗ HTML doesn't start with DOCTYPE")
            return False

        if "Duplicate Image Review" not in html:
            print("  ✗ HTML missing expected title")
            return False

        print(f"  ✓ HTML generated ({len(html)} chars)")
        return True
    except Exception as e:
        print(f"  ✗ HTML generation test failed: {e}")
        return False


def test_handler_creation():
    """Test HTTP handler creation."""
    print("\nTesting HTTP handler creation...")

    try:
        from review_app.core import DetectionAPI
        from review_app.server import create_handler_class

        base_dir = Path("/tmp/test")
        api = DetectionAPI()

        handler_class = create_handler_class(base_dir, api, None)
        print("  ✓ Handler class created")

        if handler_class.base_dir != base_dir:
            print("  ✗ Handler base_dir not set correctly")
            return False

        if handler_class.detection_api != api:
            print("  ✗ Handler detection_api not set correctly")
            return False

        print("  ✓ Handler dependencies injected correctly")
        return True
    except Exception as e:
        print(f"  ✗ Handler creation test failed: {e}")
        return False


def test_species_list():
    """Test getting species list (if test data exists)."""
    print("\nTesting species list...")

    try:
        from review_app.core import DetectionAPI

        # Try common test directories
        test_dirs = [
            Path("data/images/by_species"),
            Path("../../data/images/by_species"),
        ]

        api = DetectionAPI()

        for test_dir in test_dirs:
            if test_dir.exists():
                species = api.get_species_list(test_dir)
                print(f"  ✓ Found {len(species)} species in {test_dir}")
                if species:
                    print(f"    Examples: {species[:3]}")
                return True

        print("  ⚠ No test data directory found (this is OK)")
        return True
    except Exception as e:
        print(f"  ✗ Species list test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Refactored Review Application")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("DetectionAPI", test_detection_api),
        ("HTML Generation", test_html_generation),
        ("Handler Creation", test_handler_creation),
        ("Species List", test_species_list),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
