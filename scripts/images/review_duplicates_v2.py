#!/usr/bin/env python3
"""
Web-based Duplicate Image Review Tool (Refactored Version)

A local web server that provides a visual interface for reviewing duplicate
image groups detected by the deduplication system.

This refactored version splits the monolithic script into modular components:
- review_app/core/storage.py: FAISS embedding store
- review_app/core/detection.py: Duplicate and CNN detection logic
- review_app/core/api.py: Detection API with cache management
- review_app/server/handlers.py: HTTP request handlers
- review_app/server/html_template.py: HTML/CSS/JS generation

Usage:
    python review_duplicates_v2.py /path/to/by_species
    python review_duplicates_v2.py /path/to/by_species --port 8080

Then open http://localhost:8000 in your browser.

Dependencies:
    pip install Pillow imagehash torch torchvision faiss-cpu
"""

import argparse
import socketserver
import sys
from pathlib import Path

# Import the modular components
from review_app.core import DetectionAPI, init_faiss_store
from review_app.server import create_handler_class


def find_embeddings_dir() -> Path:
    """
    Find embeddings directory by checking common locations.

    Returns the first valid path found, with diagnostic output.
    """
    # Option 1: Relative to script location (most reliable)
    script_dir = Path(__file__).parent.parent.parent  # Go up to project root
    option1 = script_dir / "data" / "databases" / "embeddings"

    # Option 2: Relative to current directory (backwards compatibility)
    option2 = Path("data/databases/embeddings")

    # Option 3: Absolute path (fallback for this specific setup)
    option3 = Path(
        "/Users/kryticyz/Documents/life/CISS/plantNet/data/databases/embeddings"
    )

    # Check each location
    for path in [option1, option2, option3]:
        if path.exists() and (path / "embeddings.index").exists():
            print(f"✓ Found embeddings at: {path.absolute()}")
            return path

    # None found - show diagnostic and return default
    print(f"⚠️  No embeddings found. Searched:")
    print(f"   1. {option1.absolute()}")
    print(f"   2. {option2.absolute()}")
    print(f"   3. {option3.absolute()}")
    print(f"\n   Tip: Generate embeddings with batch_generate_embeddings.py")
    print(f"        or specify path with --embeddings flag")

    return option1  # Return first option as default


# Find embeddings directory at module load time
EMBEDDINGS_DIR = find_embeddings_dir()


def run_server(base_dir: Path, port: int = 8000, embeddings_dir: Path = None):
    """
    Start the duplicate review server.

    Args:
        base_dir: Base directory containing species subdirectories
        port: Port to run the server on
        embeddings_dir: Path to embeddings directory (if None, use auto-detected path)
    """
    # Use provided path or auto-detected path
    if embeddings_dir is None:
        embeddings_dir = EMBEDDINGS_DIR

    # Initialize FAISS store if available
    faiss_store = init_faiss_store(embeddings_dir)
    if faiss_store:
        print(
            f"✓ Loaded FAISS vector database with {faiss_store.index.ntotal} embeddings"
        )
        print(f"  Location: {embeddings_dir.absolute()}")
    else:
        print("ℹ  FAISS vector database not available (using on-demand computation)")

    # Create detection API with caches
    detection_api = DetectionAPI(faiss_store=faiss_store)

    # Create handler class with injected dependencies
    handler_class = create_handler_class(base_dir, detection_api, faiss_store)

    # Start the server
    with socketserver.TCPServer(("", port), handler_class) as httpd:
        print(f"\n{'=' * 60}")
        print(f"🌿 Duplicate Image Review Server (v2.0)")
        print(f"{'=' * 60}")
        print(f"Base directory: {base_dir}")
        print(f"Server running at: http://localhost:{port}")
        print(f"{'=' * 60}")
        print(f"\nPress Ctrl+C to stop the server.\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web-based duplicate image review tool (refactored).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/by_species
  %(prog)s /path/to/by_species --port 8080
  %(prog)s data/images/by_species

Then open http://localhost:8000 in your browser.

Features:
  - Perceptual hash-based duplicate detection
  - CNN-based semantic similarity detection
  - FAISS-accelerated similarity search (if embeddings pre-computed)
  - Interactive web UI with image preview
  - Batch deletion with confirmation
  - Client-side caching for performance
        """,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Base directory containing species subdirectories",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )

    parser.add_argument(
        "-e",
        "--embeddings",
        type=Path,
        default=None,
        help="Path to embeddings directory (default: auto-detect)",
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Start the server with optional embeddings path
    run_server(args.directory, args.port, args.embeddings)


if __name__ == "__main__":
    main()
