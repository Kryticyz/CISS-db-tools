#!/usr/bin/env python3
"""
PlantNet Image Review Web Application (v3)

FastAPI-based web application for reviewing plant images with
duplicate detection, similarity analysis, and outlier detection.

Usage:
    python main.py /path/to/species/directory
    python main.py data/images/by_species --port 8000
"""

import argparse
import sys
from pathlib import Path

# Add the package directory to sys.path for direct script execution
_package_dir = Path(__file__).parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))
# Also add parent for importing existing core modules
_scripts_images_dir = _package_dir.parent
if str(_scripts_images_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_images_dir))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.deps import init_services
from api.routes import (
    analysis_router,
    dashboard_router,
    deletion_router,
    images_router,
)
from config import init_settings, get_settings


def create_app(
    base_dir: Path,
    embeddings_dir: Path | None = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        base_dir: Base directory containing species folders
        embeddings_dir: Directory containing FAISS embeddings

    Returns:
        Configured FastAPI application
    """
    # Initialize settings
    settings = init_settings(
        base_dir=base_dir,
        embeddings_dir=embeddings_dir or Path("data/databases/embeddings"),
    )

    # Validate base directory
    if not settings.base_dir.exists():
        raise ValueError(f"Base directory not found: {settings.base_dir}")

    if not settings.base_dir.is_dir():
        raise ValueError(f"Base directory is not a directory: {settings.base_dir}")

    # Check for species directories
    species_dirs = [
        d for d in settings.base_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    if not species_dirs:
        raise ValueError(f"No species directories found in: {settings.base_dir}")

    # Create FastAPI app
    app = FastAPI(
        title="PlantNet Image Review",
        description="Web application for reviewing plant images with duplicate, similarity, and outlier detection.",
        version="3.0.0",
    )

    # Add CORS middleware for React dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services
    try:
        init_services(settings)
    except Exception as e:
        print(f"Error initializing services: {e}", file=sys.stderr)
        raise

    # Register API routes
    app.include_router(dashboard_router)
    app.include_router(analysis_router)
    app.include_router(images_router)
    app.include_router(deletion_router)

    # Serve React frontend in production
    frontend_dist = Path(__file__).parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="PlantNet Image Review Web Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m review_app_v3.main data/images/by_species
    python -m review_app_v3.main /path/to/images --port 8080
    python -m review_app_v3.main data/images/by_species --embeddings data/databases/embeddings
        """,
    )

    parser.add_argument(
        "base_dir",
        type=Path,
        help="Base directory containing species image folders",
    )

    parser.add_argument(
        "--embeddings",
        type=Path,
        default=None,
        help="Directory containing FAISS embeddings (default: data/databases/embeddings)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    # Resolve paths
    base_dir = args.base_dir.resolve()
    embeddings_dir = args.embeddings.resolve() if args.embeddings else None

    # Validate base directory
    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}", file=sys.stderr)
        sys.exit(1)

    # Create app
    try:
        app = create_app(base_dir, embeddings_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print startup info
    print(f"\n{'='*60}")
    print("PlantNet Image Review Web Application")
    print(f"{'='*60}")
    print(f"Base directory: {base_dir}")
    print(f"Embeddings: {embeddings_dir or 'data/databases/embeddings'}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"{'='*60}\n")

    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
