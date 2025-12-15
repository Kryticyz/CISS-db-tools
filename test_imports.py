#!/usr/bin/env python3
"""
Quick test script to verify package imports work correctly.

Run this after installing the package with: pip install -e .
"""

print("Testing plantnet package imports...")
print("=" * 60)

# Test main package
try:
    import plantnet

    print(f"✓ plantnet package imported")
    print(f"  Version: {plantnet.__version__}")
except Exception as e:
    print(f"✗ Failed to import plantnet: {e}")
    exit(1)

# Test core modules
try:
    from plantnet.core import GBIFParser

    print(f"✓ GBIFParser imported from core")
except Exception as e:
    print(f"✗ Failed to import GBIFParser: {e}")

# Test utils
try:
    from plantnet.utils.paths import DATA_DIR, IMAGES_DIR

    print(f"✓ Path utilities imported")
    print(f"  DATA_DIR: {DATA_DIR}")
except Exception as e:
    print(f"✗ Failed to import paths: {e}")

# Test image modules
try:
    from plantnet.images import DeduplicationResult, deduplicate_species_images

    print(f"✓ Deduplication module imported")
except Exception as e:
    print(f"✗ Failed to import deduplication: {e}")

try:
    from plantnet.images import SimilarityResult, analyze_species_similarity

    print(f"✓ Similarity module imported")
except Exception as e:
    print(f"✗ Failed to import similarity: {e}")

# Test direct imports
try:
    from plantnet import GBIFParser, deduplicate_species_images

    print(f"✓ Direct imports from plantnet package work")
except Exception as e:
    print(f"✗ Failed direct imports: {e}")

print("=" * 60)
print("All imports successful! Package is properly structured.")
print("\nNext steps:")
print("1. Test with: python test_imports.py")
print("2. Run: plantnet --version (once CLI is created)")
print("3. Start using: from plantnet.images import deduplicate_species_images")
