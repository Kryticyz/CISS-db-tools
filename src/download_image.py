#!/usr/bin/env python3
"""
Script to download an image from a URL and save it to ./data directory.
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install it with: pip install requests")
    sys.exit(1)


def get_filename_from_url(url):
    """Extract filename from URL."""
    parsed_url = urlparse(url)
    path = unquote(parsed_url.path)
    filename = os.path.basename(path)

    # If no filename found or it doesn't have an extension, generate one
    if not filename or "." not in filename:
        filename = f"{filename}.jpg"

    return filename


def download_image(url, output_dir="./data"):
    """
    Download an image from the given URL and save it to the output directory.

    Args:
        url (str): URL of the image to download
        output_dir (str): Directory to save the image (default: ./data)

    Returns:
        str: Path to the downloaded file
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        # Send GET request
        print(f"Downloading image from: {url}")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        # Check if content type is an image
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            print(f"Warning: Content-Type is '{content_type}', not an image type")

        # Get filename
        filename = get_filename_from_url(url)
        filepath = os.path.join(output_dir, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filepath):
                filename = f"{base}_{counter}{ext}"
                filepath = os.path.join(output_dir, filename)
                counter += 1
            print(f"File already exists, saving as: {filename}")

        # Save image
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Image successfully downloaded to: {filepath}")
        return filepath

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download an image from a URL to ./data directory"
    )
    parser.add_argument("url", help="URL of the image to download")
    parser.add_argument(
        "-o", "--output", default="./data", help="Output directory (default: ./data)"
    )

    args = parser.parse_args()

    download_image(args.url, args.output)


if __name__ == "__main__":
    main()
