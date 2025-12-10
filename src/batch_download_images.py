#!/usr/bin/env python3
"""
Script to batch download images from a text file containing URLs.
Uses the download_image module to download each image.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Import the download_image module
try:
    from download_image import download_image
except ImportError:
    print("Error: Cannot import download_image module.")
    print(
        "Make sure download_image.py is in the same directory or in your Python path."
    )
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install it with: pip install requests")
    sys.exit(1)


def read_urls_from_file(filepath):
    """
    Read URLs from a text file, one per line.
    Skips empty lines and lines starting with #.

    Args:
        filepath: Path to the text file containing URLs

    Returns:
        List of URLs
    """
    urls = []
    try:
        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Basic URL validation
                if line.startswith("http://") or line.startswith("https://"):
                    urls.append(line)
                else:
                    print(
                        f"Warning: Line {line_num} doesn't look like a URL, skipping: {line[:50]}"
                    )

        return urls
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def download_single_image(url, output_dir, index, total):
    """
    Download a single image with error handling.

    Args:
        url: URL to download
        output_dir: Directory to save the image
        index: Current image number
        total: Total number of images

    Returns:
        Tuple of (success, url, filepath or error_message)
    """
    try:
        print(f"\n[{index}/{total}] Downloading: {url}")
        filepath = download_image(url, output_dir)
        return (True, url, filepath)
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Failed to download {url}: {error_msg}")
        return (False, url, error_msg)


def batch_download(urls, output_dir="./dump", max_workers=5, delay=0):
    """
    Download multiple images from a list of URLs.

    Args:
        urls: List of URLs to download
        output_dir: Directory to save images
        max_workers: Number of concurrent downloads (default: 5)
        delay: Delay in seconds between downloads (default: 0)

    Returns:
        Dictionary with success and failure counts
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    total = len(urls)
    successful = []
    failed = []

    print(f"\n{'=' * 70}")
    print(f"Starting batch download of {total} images")
    print(f"Output directory: {output_dir}")
    print(f"Concurrent downloads: {max_workers}")
    print(f"{'=' * 70}\n")

    start_time = time.time()

    if max_workers == 1:
        # Sequential download
        for i, url in enumerate(urls, 1):
            success, url, result = download_single_image(url, output_dir, i, total)
            if success:
                successful.append((url, result))
            else:
                failed.append((url, result))

            # Add delay between downloads if specified
            if delay > 0 and i < total:
                time.sleep(delay)
    else:
        # Concurrent download
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(download_single_image, url, output_dir, i, total): (
                    i,
                    url,
                )
                for i, url in enumerate(urls, 1)
            }

            # Process completed downloads
            for future in as_completed(future_to_url):
                success, url, result = future.result()
                if success:
                    successful.append((url, result))
                else:
                    failed.append((url, result))

                # Add delay if specified
                if delay > 0:
                    time.sleep(delay)

    end_time = time.time()
    duration = end_time - start_time

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"Download Complete!")
    print(f"{'=' * 70}")
    print(f"Total URLs: {total}")
    print(f"Successful: {len(successful)} ({len(successful) / total * 100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed) / total * 100:.1f}%)")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Average: {duration / total:.2f} seconds per image")
    print(f"{'=' * 70}\n")

    # Print failed URLs if any
    if failed:
        print("Failed downloads:")
        for url, error in failed:
            print(f"  ✗ {url}")
            print(f"    Error: {error}")
        print()

    return {
        "total": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_list": successful,
        "failure_list": failed,
        "duration": duration,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Batch download images from a text file containing URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all images from verbena_urls.txt to dump directory
  python src/batch_download_images.py verbena_urls.txt

  # Download to a custom directory
  python src/batch_download_images.py verbena_urls.txt --output ./my_images

  # Use 10 concurrent downloads
  python src/batch_download_images.py verbena_urls.txt --workers 10

  # Add 1 second delay between downloads (be nice to servers)
  python src/batch_download_images.py verbena_urls.txt --delay 1

  # Sequential download (no concurrency)
  python src/batch_download_images.py verbena_urls.txt --workers 1

  # Save failed URLs to a file for retry
  python src/batch_download_images.py verbena_urls.txt --save-failed failed.txt
        """,
    )

    parser.add_argument("url_file", help="Text file containing URLs (one per line)")
    parser.add_argument(
        "-o",
        "--output",
        default="./dump",
        help="Output directory for downloaded images (default: ./dump)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent downloads (default: 5, use 1 for sequential)",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=0,
        help="Delay in seconds between downloads (default: 0)",
    )
    parser.add_argument(
        "--save-failed", help="Save failed URLs to this file for later retry"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of URLs to download (for testing)"
    )

    args = parser.parse_args()

    # Read URLs from file
    print(f"Reading URLs from: {args.url_file}")
    urls = read_urls_from_file(args.url_file)

    if not urls:
        print("Error: No valid URLs found in file")
        sys.exit(1)

    print(f"Found {len(urls)} URLs")

    # Apply limit if specified
    if args.limit:
        urls = urls[: args.limit]
        print(f"Limiting to first {len(urls)} URLs")

    # Download images
    results = batch_download(
        urls, output_dir=args.output, max_workers=args.workers, delay=args.delay
    )

    # Save failed URLs if requested
    if args.save_failed and results["failure_list"]:
        with open(args.save_failed, "w") as f:
            f.write("# Failed URLs from batch download\n")
            f.write(f"# Original file: {args.url_file}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for url, error in results["failure_list"]:
                f.write(f"{url}\n")
                f.write(f"# Error: {error}\n")
        print(f"Failed URLs saved to: {args.save_failed}")

    # Exit with error code if any downloads failed
    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
