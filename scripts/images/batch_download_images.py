#!/usr/bin/env python3
"""
Script to batch download images from a directory containing URL text files.
Processes all *_urls.txt files in the species_urls directory and downloads
images to species-specific subdirectories.
"""

import argparse
import random
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
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []


def download_single_image(url, output_dir, index, total, max_retries=3):
    """
    Download a single image with error handling and retry logic.

    Args:
        url: URL to download
        output_dir: Directory to save the image
        index: Current image number
        total: Total number of images
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Tuple of (success, url, filepath or error_message)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            if attempt == 0:
                print(f"  [{index}/{total}] Downloading: {url}")
            else:
                print(f"  [{index}/{total}] Retry {attempt}/{max_retries - 1}: {url}")

            filepath = download_image(url, output_dir)
            return (True, url, filepath)

        except requests.exceptions.SSLError as e:
            last_error = f"SSL Error: {str(e)}"
            # SSL errors are usually not transient, don't retry
            print(f"  ✗ SSL Error downloading {url}: {last_error}")
            return (False, url, last_error)

        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection Error: {str(e)}"
            # Connection errors might be transient, retry with backoff
            if attempt < max_retries - 1:
                backoff = (2**attempt) + random.uniform(0, 1)
                print(
                    f"  ⚠ Connection Error (attempt {attempt + 1}/{max_retries}), retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
            else:
                print(
                    f"  ✗ Connection Error downloading {url} after {max_retries} attempts: {last_error}"
                )

        except requests.exceptions.Timeout as e:
            last_error = f"Timeout Error: {str(e)}"
            # Timeouts are often transient, retry with backoff
            if attempt < max_retries - 1:
                backoff = (2**attempt) + random.uniform(0, 1)
                print(
                    f"  ⚠ Timeout (attempt {attempt + 1}/{max_retries}), retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
            else:
                print(
                    f"  ✗ Timeout downloading {url} after {max_retries} attempts: {last_error}"
                )

        except requests.exceptions.RequestException as e:
            last_error = f"Request Error: {str(e)}"
            # Generic request errors might be transient
            if attempt < max_retries - 1:
                backoff = (2**attempt) + random.uniform(0, 1)
                print(
                    f"  ⚠ Request Error (attempt {attempt + 1}/{max_retries}), retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
            else:
                print(
                    f"  ✗ Request Error downloading {url} after {max_retries} attempts: {last_error}"
                )

        except Exception as e:
            last_error = f"Unexpected Error: {str(e)}"
            print(f"  ✗ Failed to download {url}: {last_error}")
            return (False, url, last_error)

    # If we exhausted all retries
    return (False, url, last_error)


def batch_download(urls, output_dir="./dump", max_workers=5, delay=0, max_retries=3):
    """
    Download multiple images from a list of URLs.

    Args:
        urls: List of URLs to download
        output_dir: Directory to save images
        max_workers: Number of concurrent downloads (default: 5)
        delay: Delay in seconds between downloads (default: 0)
        max_retries: Maximum number of retry attempts per URL (default: 3)

    Returns:
        Dictionary with success and failure counts
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    total = len(urls)
    successful = []
    failed = []

    start_time = time.time()

    if max_workers == 1:
        # Sequential download
        for i, url in enumerate(urls, 1):
            success, url, result = download_single_image(
                url, output_dir, i, total, max_retries
            )
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
                executor.submit(
                    download_single_image, url, output_dir, i, total, max_retries
                ): (
                    i,
                    url,
                )
                for i, url in enumerate(urls, 1)
            }

            # Process completed downloads
            for future in as_completed(future_to_url):
                i, url = future_to_url[future]
                try:
                    success, url, result = future.result()
                    if success:
                        successful.append((url, result))
                    else:
                        failed.append((url, result))
                except Exception as e:
                    # Handle any exceptions that weren't caught in download_single_image
                    error_msg = f"Unexpected error: {str(e)}"
                    print(f"  ✗ Failed to process {url}: {error_msg}")
                    failed.append((url, error_msg))

                # Add delay if specified
                if delay > 0:
                    time.sleep(delay)

    end_time = time.time()
    duration = end_time - start_time

    return {
        "total": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_list": successful,
        "failure_list": failed,
        "duration": duration,
    }


def get_species_name_from_file(filepath):
    """
    Extract species name from URL filename.
    E.g., 'Acacia_baileyana_urls.txt' -> 'Acacia_baileyana'

    Args:
        filepath: Path to the URL file

    Returns:
        Species name string
    """
    filename = Path(filepath).stem  # Remove .txt extension
    if filename.endswith("_urls"):
        return filename[:-5]  # Remove '_urls' suffix
    return filename


def find_url_files(directory):
    """
    Find all URL text files in the given directory.

    Args:
        directory: Path to the directory containing URL files

    Returns:
        List of Path objects for each URL file
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)
    if not dir_path.is_dir():
        print(f"Error: Not a directory: {directory}")
        sys.exit(1)

    # Find all *_urls.txt files
    url_files = sorted(dir_path.glob("*_urls.txt"))
    return url_files


def process_single_species(
    species_idx,
    total_species,
    url_file,
    output_base_dir,
    max_workers,
    delay,
    limit_per_species,
    max_retries=3,
):
    """
    Process a single species URL file and download its images.

    Args:
        species_idx: Index of this species (for display)
        total_species: Total number of species being processed
        url_file: Path to the URL file
        output_base_dir: Base directory for output
        max_workers: Number of concurrent downloads
        delay: Delay between downloads
        limit_per_species: Optional limit on URLs per species
        max_retries: Maximum number of retry attempts per URL

    Returns:
        Tuple of (species_name, results_dict)
    """
    species_name = get_species_name_from_file(url_file)
    species_output_dir = Path(output_base_dir) / species_name

    print(f"\n[{species_idx}/{total_species}] Processing: {species_name}")
    print(f"-" * 50)

    # Read URLs from file
    urls = read_urls_from_file(url_file)
    if not urls:
        print("  No valid URLs found, skipping...")
        return (species_name, None)

    # Apply limit if specified
    if limit_per_species and len(urls) > limit_per_species:
        urls = urls[:limit_per_species]
        print(f"  Limiting to {limit_per_species} URLs")

    print(f"  Found {len(urls)} URLs")
    print(f"  Output: {species_output_dir}")

    # Download images for this species
    results = batch_download(
        urls,
        output_dir=str(species_output_dir),
        max_workers=max_workers,
        delay=delay,
        max_retries=max_retries,
    )

    # Print species summary
    print(
        f"  ✓ Completed: {results['successful']}/{results['total']} successful ({results['duration']:.2f}s)"
    )

    return (species_name, results)


def process_directory(
    url_dir,
    output_base_dir="./dump",
    max_workers=5,
    delay=0,
    limit_per_species=None,
    species_filter=None,
    parallel_species=False,
    max_retries=3,
):
    """
    Process all URL files in a directory, downloading images for each species.

    Args:
        url_dir: Directory containing URL text files
        output_base_dir: Base directory for output (species subdirs will be created)
        max_workers: Number of concurrent downloads
        delay: Delay between downloads
        limit_per_species: Optional limit on URLs per species
        species_filter: Optional list of species names to process (if None, process all)
        parallel_species: If True, process species files in parallel (one worker per species)
        max_retries: Maximum number of retry attempts per URL

    Returns:
        Dictionary with overall results
    """
    url_files = find_url_files(url_dir)

    if not url_files:
        print(f"Error: No URL files found in {url_dir}")
        sys.exit(1)

    # Filter species if specified
    if species_filter:
        filtered_files = []
        for f in url_files:
            species_name = get_species_name_from_file(f)
            if species_name in species_filter:
                filtered_files.append(f)
        url_files = filtered_files
        if not url_files:
            print("Error: No matching species found for filter")
            sys.exit(1)

    total_species = len(url_files)
    print(f"\n{'=' * 70}")
    print(f"Processing {total_species} species from: {url_dir}")
    print(f"Output base directory: {output_base_dir}")
    print(f"Concurrent downloads: {max_workers}")
    if limit_per_species:
        print(f"Limit per species: {limit_per_species}")
    if parallel_species:
        print(f"Parallel species processing: ENABLED (one worker per species)")
    print(f"{'=' * 70}\n")

    overall_start_time = time.time()
    overall_results = {
        "total_species": total_species,
        "total_urls": 0,
        "total_successful": 0,
        "total_failed": 0,
        "species_results": {},
    }

    all_failed = []

    if parallel_species:
        # Parallel species processing - one worker thread per species
        print("Processing species in parallel (one worker per species)...\n")

        with ThreadPoolExecutor(max_workers=total_species) as executor:
            # Submit all species processing tasks
            future_to_species = {
                executor.submit(
                    process_single_species,
                    i,
                    total_species,
                    url_file,
                    output_base_dir,
                    max_workers,
                    delay,
                    limit_per_species,
                    max_retries,
                ): url_file
                for i, url_file in enumerate(url_files, 1)
            }

            # Process completed species
            for future in as_completed(future_to_species):
                try:
                    species_name, results = future.result()

                    if results is None:
                        # No valid URLs found for this species
                        continue

                    # Update overall results
                    overall_results["total_urls"] += results["total"]
                    overall_results["total_successful"] += results["successful"]
                    overall_results["total_failed"] += results["failed"]
                    overall_results["species_results"][species_name] = results

                    # Collect failed downloads
                    for url, error in results["failure_list"]:
                        all_failed.append((species_name, url, error))

                except Exception as e:
                    url_file = future_to_species[future]
                    species_name = get_species_name_from_file(url_file)
                    print(f"  ✗ Failed to process species {species_name}: {str(e)}")
    else:
        # Sequential species processing
        for species_idx, url_file in enumerate(url_files, 1):
            species_name, results = process_single_species(
                species_idx,
                total_species,
                url_file,
                output_base_dir,
                max_workers,
                delay,
                limit_per_species,
                max_retries,
            )

            if results is None:
                # No valid URLs found for this species
                continue

            # Update overall results
            overall_results["total_urls"] += results["total"]
            overall_results["total_successful"] += results["successful"]
            overall_results["total_failed"] += results["failed"]
            overall_results["species_results"][species_name] = results

            # Collect failed downloads
            for url, error in results["failure_list"]:
                all_failed.append((species_name, url, error))

    overall_end_time = time.time()
    overall_duration = overall_end_time - overall_start_time

    # Print overall summary
    print(f"\n{'=' * 70}")
    print(f"OVERALL SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total species processed: {total_species}")
    print(f"Total URLs: {overall_results['total_urls']}")
    print(
        f"Successful downloads: {overall_results['total_successful']} ({overall_results['total_successful'] / max(overall_results['total_urls'], 1) * 100:.1f}%)"
    )
    print(
        f"Failed downloads: {overall_results['total_failed']} ({overall_results['total_failed'] / max(overall_results['total_urls'], 1) * 100:.1f}%)"
    )
    print(f"Total time: {overall_duration:.2f} seconds")
    print(f"{'=' * 70}\n")

    overall_results["duration"] = overall_duration
    overall_results["all_failed"] = all_failed

    return overall_results


def main():
    parser = argparse.ArgumentParser(
        description="Batch download images from a directory containing URL text files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all species from the species_urls directory
  python src/batch_download_images.py species_urls

  # Download to a custom directory
  python src/batch_download_images.py species_urls --output ./images

  # Use 10 concurrent downloads
  python src/batch_download_images.py species_urls --workers 10

  # Add 1 second delay between downloads (be nice to servers)
  python src/batch_download_images.py species_urls --delay 1

  # Limit to 50 images per species
  python src/batch_download_images.py species_urls --limit 50

  # Process only specific species
  python src/batch_download_images.py species_urls --species Acacia_baileyana Acacia_dealbata

  # Process all species in parallel (one worker thread per species)
  python src/batch_download_images.py species_urls --parallel-species

  # Save failed URLs to a file for retry
  python src/batch_download_images.py species_urls --save-failed failed.txt

Troubleshooting:
  If you encounter SSL errors (e.g., "Max retries exceeded", "SSLError"):
  - Reduce concurrent workers (--workers 2 or --workers 1)
  - Add delay between requests (--delay 1 or higher)
  - Avoid --parallel-species if the server is rate-limiting
  - Retry failed URLs later using the --save-failed output file

  Example for problematic servers:
  python src/batch_download_images.py species_urls --workers 2 --delay 2 --save-failed failed.txt
        """,
    )

    parser.add_argument(
        "url_dir",
        nargs="?",
        default="./data/processed/species_urls",
        help="Directory containing URL text files (default: ./data/processed/species_urls)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./data/images/by_species",
        help="Base output directory for downloaded images (default: ./data/images/by_species)",
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
        "--save-failed",
        help="Save failed URLs to this file for later retry",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of URLs to download per species (for testing)",
    )
    parser.add_argument(
        "--species",
        nargs="+",
        help="Only process specific species (by name, e.g., Acacia_baileyana)",
    )
    parser.add_argument(
        "--parallel-species",
        action="store_true",
        help="Process species files in parallel (one worker thread per species)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts for failed downloads (default: 3)",
    )

    args = parser.parse_args()

    # Process the directory
    results = process_directory(
        url_dir=args.url_dir,
        output_base_dir=args.output,
        max_workers=args.workers,
        delay=args.delay,
        limit_per_species=args.limit,
        species_filter=args.species,
        parallel_species=args.parallel_species,
        max_retries=args.max_retries,
    )

    # Save failed URLs if requested
    if args.save_failed and results["all_failed"]:
        with open(args.save_failed, "w") as f:
            f.write("# Failed URLs from batch download\n")
            f.write(f"# Source directory: {args.url_dir}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total failed: {len(results['all_failed'])}\n\n")

            current_species = None
            for species, url, error in results["all_failed"]:
                if species != current_species:
                    f.write(f"\n# Species: {species}\n")
                    current_species = species
                f.write(f"{url}\n")
                f.write(f"# Error: {error}\n")
        print(f"\nFailed URLs saved to: {args.save_failed}")
        print(f"Total failed: {len(results['all_failed'])}")

    # Exit with error code if any downloads failed
    if results["total_failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
