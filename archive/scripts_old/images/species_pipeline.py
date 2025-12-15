#!/usr/bin/env python3
"""
Species Pipeline Orchestrator

This script orchestrates the execution of image processing functions across
species directories. It supports:
- Running multiple processing steps in sequence per species
- Parallel execution across species
- Progress tracking and reporting
- Consolidated output reports

Usage:
    # Process all species with deduplication
    python species_pipeline.py /path/to/by_species

    # Process specific species with 4 parallel workers
    python species_pipeline.py /path/to/by_species --workers 4 --species Acacia_baileyana Acacia_saligna

    # Dry run to see what would be processed
    python species_pipeline.py /path/to/by_species --dry-run

Dependencies:
    pip install Pillow imagehash
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import processing modules
try:
    from deduplicate_images import DeduplicationResult, deduplicate_species_images
except ImportError:
    # Handle case where script is run from different directory
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from deduplicate_images import DeduplicationResult, deduplicate_species_images


@dataclass
class PipelineStepResult:
    """Result from a single pipeline step."""

    step_name: str
    success: bool
    duration: float
    result_data: Any = None
    error: Optional[str] = None


@dataclass
class SpeciesPipelineResult:
    """Result from processing a single species through the pipeline."""

    species_name: str
    directory: Path
    total_duration: float
    steps_completed: int
    steps_failed: int
    step_results: List[PipelineStepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.steps_failed == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "species_name": self.species_name,
            "directory": str(self.directory),
            "total_duration": self.total_duration,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "success": self.success,
            "step_results": [
                {
                    "step_name": sr.step_name,
                    "success": sr.success,
                    "duration": sr.duration,
                    "error": sr.error,
                    "result_data": (
                        sr.result_data.to_dict()
                        if hasattr(sr.result_data, "to_dict")
                        else sr.result_data
                    ),
                }
                for sr in self.step_results
            ],
        }


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""

    # Deduplication settings
    dedup_hash_size: int = 16
    dedup_hamming_threshold: int = 5
    dedup_use_file_hash: bool = False
    dedup_max_workers: Optional[int] = None

    # Pipeline settings
    output_dir: Optional[Path] = None
    verbose: bool = True

    # Steps to run (in order)
    steps: List[str] = field(default_factory=lambda: ["deduplicate"])


# Registry of available pipeline steps
PIPELINE_STEPS: Dict[str, Callable] = {}


def register_step(name: str):
    """Decorator to register a pipeline step function."""

    def decorator(func: Callable):
        PIPELINE_STEPS[name] = func
        return func

    return decorator


@register_step("deduplicate")
def step_deduplicate(
    species_dir: Path, config: PipelineConfig, previous_results: Dict[str, Any]
) -> Tuple[bool, Any, Optional[str]]:
    """
    Deduplication step: detect and mark duplicate images.

    Args:
        species_dir: Path to species directory
        config: Pipeline configuration
        previous_results: Results from previous steps (unused here)

    Returns:
        Tuple of (success, result_data, error_message)
    """
    try:
        result = deduplicate_species_images(
            species_directory=species_dir,
            output_dir=config.output_dir or species_dir,
            hash_size=config.dedup_hash_size,
            hamming_threshold=config.dedup_hamming_threshold,
            max_workers=config.dedup_max_workers,
            use_file_hash=config.dedup_use_file_hash,
            verbose=config.verbose,
        )

        # Check for critical errors
        if result.errors and result.total_images == 0:
            return (False, result, f"Failed to process any images: {result.errors}")

        return (True, result, None)

    except Exception as e:
        return (False, None, str(e))


# Placeholder for future steps - add more as needed
@register_step("validate")
def step_validate(
    species_dir: Path, config: PipelineConfig, previous_results: Dict[str, Any]
) -> Tuple[bool, Any, Optional[str]]:
    """
    Validation step: validate image integrity (placeholder for future implementation).

    Args:
        species_dir: Path to species directory
        config: Pipeline configuration
        previous_results: Results from previous steps

    Returns:
        Tuple of (success, result_data, error_message)
    """
    # Placeholder - implement actual validation logic as needed
    return (True, {"validated": True, "species": species_dir.name}, None)


@register_step("resize")
def step_resize(
    species_dir: Path, config: PipelineConfig, previous_results: Dict[str, Any]
) -> Tuple[bool, Any, Optional[str]]:
    """
    Resize step: resize images to standard dimensions (placeholder for future implementation).

    Args:
        species_dir: Path to species directory
        config: Pipeline configuration
        previous_results: Results from previous steps

    Returns:
        Tuple of (success, result_data, error_message)
    """
    # Placeholder - implement actual resize logic as needed
    return (True, {"resized": True, "species": species_dir.name}, None)


def process_species(species_dir: Path, config: PipelineConfig) -> SpeciesPipelineResult:
    """
    Process a single species through all pipeline steps.

    Steps are executed in sequence, with results from each step
    available to subsequent steps.

    Args:
        species_dir: Path to the species directory
        config: Pipeline configuration

    Returns:
        SpeciesPipelineResult with details of all steps
    """
    species_name = species_dir.name
    start_time = time.time()

    result = SpeciesPipelineResult(
        species_name=species_name,
        directory=species_dir,
        total_duration=0,
        steps_completed=0,
        steps_failed=0,
    )

    if config.verbose:
        print(f"\n{'=' * 60}")
        print(f"Processing species: {species_name}")
        print(f"{'=' * 60}")

    # Collect results from previous steps for potential use by later steps
    previous_results: Dict[str, Any] = {}

    for step_name in config.steps:
        if step_name not in PIPELINE_STEPS:
            if config.verbose:
                print(f"  Warning: Unknown step '{step_name}', skipping")
            continue

        step_func = PIPELINE_STEPS[step_name]
        step_start = time.time()

        if config.verbose:
            print(f"\n  [{species_name}] Running step: {step_name}")

        try:
            success, step_data, error = step_func(species_dir, config, previous_results)
            step_duration = time.time() - step_start

            step_result = PipelineStepResult(
                step_name=step_name,
                success=success,
                duration=step_duration,
                result_data=step_data,
                error=error,
            )

            result.step_results.append(step_result)

            if success:
                result.steps_completed += 1
                previous_results[step_name] = step_data
                if config.verbose:
                    print(
                        f"  [{species_name}] Step '{step_name}' completed in {step_duration:.2f}s"
                    )
            else:
                result.steps_failed += 1
                if config.verbose:
                    print(f"  [{species_name}] Step '{step_name}' FAILED: {error}")

        except Exception as e:
            step_duration = time.time() - step_start
            step_result = PipelineStepResult(
                step_name=step_name,
                success=False,
                duration=step_duration,
                error=str(e),
            )
            result.step_results.append(step_result)
            result.steps_failed += 1

            if config.verbose:
                print(f"  [{species_name}] Step '{step_name}' EXCEPTION: {e}")

    result.total_duration = time.time() - start_time

    if config.verbose:
        status = "SUCCESS" if result.success else "FAILED"
        print(f"\n  [{species_name}] Pipeline {status} in {result.total_duration:.2f}s")
        print(
            f"  [{species_name}] Steps: {result.steps_completed} completed, {result.steps_failed} failed"
        )

    return result


def process_species_wrapper(args: Tuple[Path, PipelineConfig]) -> SpeciesPipelineResult:
    """
    Wrapper for process_species to work with ProcessPoolExecutor.

    Args:
        args: Tuple of (species_dir, config)

    Returns:
        SpeciesPipelineResult
    """
    species_dir, config = args
    # Reduce verbosity in parallel mode to avoid interleaved output
    config.verbose = False
    return process_species(species_dir, config)


def get_species_directories(
    base_dir: Path, species_filter: Optional[List[str]] = None
) -> List[Path]:
    """
    Get list of species directories to process.

    Args:
        base_dir: Base directory containing species subdirectories
        species_filter: Optional list of species names to process

    Returns:
        List of species directory paths
    """
    species_dirs = []

    for item in sorted(base_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            if species_filter is None or item.name in species_filter:
                species_dirs.append(item)

    return species_dirs


def run_pipeline(
    base_dir: Path,
    config: PipelineConfig,
    species_filter: Optional[List[str]] = None,
    max_parallel_species: int = 1,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run the pipeline across multiple species directories.

    Args:
        base_dir: Base directory containing species subdirectories
        config: Pipeline configuration
        species_filter: Optional list of species to process
        max_parallel_species: Number of species to process in parallel
        dry_run: If True, only show what would be processed

    Returns:
        Dictionary with overall pipeline results
    """
    start_time = time.time()

    # Get species directories
    species_dirs = get_species_directories(base_dir, species_filter)

    if not species_dirs:
        print("Error: No species directories found to process")
        return {"success": False, "error": "No species directories found"}

    print(f"\n{'=' * 70}")
    print(f"SPECIES IMAGE PROCESSING PIPELINE")
    print(f"{'=' * 70}")
    print(f"Base directory:     {base_dir}")
    print(f"Species to process: {len(species_dirs)}")
    print(f"Pipeline steps:     {', '.join(config.steps)}")
    print(f"Parallel species:   {max_parallel_species}")
    if config.output_dir:
        print(f"Output directory:   {config.output_dir}")
    print(f"{'=' * 70}\n")

    if dry_run:
        print("DRY RUN - Species that would be processed:")
        for i, species_dir in enumerate(species_dirs, 1):
            print(f"  {i:4d}. {species_dir.name}")
        return {
            "success": True,
            "dry_run": True,
            "species_count": len(species_dirs),
            "species": [d.name for d in species_dirs],
        }

    # Process species
    results: List[SpeciesPipelineResult] = []

    if max_parallel_species > 1:
        # Parallel processing
        print(f"Processing {len(species_dirs)} species in parallel...")

        with ProcessPoolExecutor(max_workers=max_parallel_species) as executor:
            # Create config copies for each worker
            future_to_species = {
                executor.submit(
                    process_species_wrapper, (species_dir, config)
                ): species_dir
                for species_dir in species_dirs
            }

            completed = 0
            for future in as_completed(future_to_species):
                species_dir = future_to_species[future]
                completed += 1
                try:
                    result = future.result()
                    results.append(result)
                    status = "✓" if result.success else "✗"
                    print(
                        f"  [{completed}/{len(species_dirs)}] {status} {result.species_name} "
                        f"({result.total_duration:.2f}s)"
                    )
                except Exception as e:
                    print(
                        f"  [{completed}/{len(species_dirs)}] ✗ {species_dir.name} EXCEPTION: {e}"
                    )
                    results.append(
                        SpeciesPipelineResult(
                            species_name=species_dir.name,
                            directory=species_dir,
                            total_duration=0,
                            steps_completed=0,
                            steps_failed=len(config.steps),
                        )
                    )
    else:
        # Sequential processing
        for i, species_dir in enumerate(species_dirs, 1):
            print(f"\n[{i}/{len(species_dirs)}] Processing {species_dir.name}...")
            result = process_species(species_dir, config)
            results.append(result)

    total_duration = time.time() - start_time

    # Generate summary
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    # Aggregate deduplication results
    total_duplicates_marked = 0
    total_images_processed = 0

    for result in results:
        for step_result in result.step_results:
            if step_result.step_name == "deduplicate" and step_result.result_data:
                dedup_result = step_result.result_data
                if hasattr(dedup_result, "duplicates_marked"):
                    total_duplicates_marked += dedup_result.duplicates_marked
                    total_images_processed += dedup_result.total_images

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total species processed:    {len(results)}")
    print(f"Successful:                 {successful}")
    print(f"Failed:                     {failed}")
    print(f"Total duration:             {total_duration:.2f}s")
    print(f"Average per species:        {total_duration / len(results):.2f}s")

    if total_images_processed > 0:
        print(f"\nDeduplication Results:")
        print(f"  Total images processed:   {total_images_processed}")
        print(f"  Total duplicates marked:  {total_duplicates_marked}")
        print(
            f"  Duplicate rate:           {total_duplicates_marked / total_images_processed * 100:.2f}%"
        )

    print(f"{'=' * 70}\n")

    # Write consolidated report
    if config.output_dir:
        report_path = config.output_dir / "pipeline_report.json"
    else:
        report_path = base_dir / "pipeline_report.json"

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "base_directory": str(base_dir),
        "total_species": len(results),
        "successful": successful,
        "failed": failed,
        "total_duration": total_duration,
        "pipeline_steps": config.steps,
        "deduplication_summary": {
            "total_images_processed": total_images_processed,
            "total_duplicates_marked": total_duplicates_marked,
        },
        "species_results": [r.to_dict() for r in results],
    }

    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"Report written to: {report_path}")

    # Write consolidated deletion list
    consolidated_deletions_path = (
        config.output_dir or base_dir
    ) / "all_duplicates_for_deletion.txt"

    with open(consolidated_deletions_path, "w") as f:
        f.write("# Consolidated list of duplicate images marked for deletion\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Total species: {len(results)}\n")
        f.write(f"# Total duplicates: {total_duplicates_marked}\n")
        f.write("#\n\n")

        for result in sorted(results, key=lambda r: r.species_name):
            for step_result in result.step_results:
                if step_result.step_name == "deduplicate" and step_result.result_data:
                    dedup_result = step_result.result_data
                    if (
                        hasattr(dedup_result, "marked_for_deletion")
                        and dedup_result.marked_for_deletion
                    ):
                        f.write(f"# Species: {result.species_name}\n")
                        for filename in dedup_result.marked_for_deletion:
                            f.write(f"{result.species_name}/{filename}\n")
                        f.write("\n")

    print(f"Consolidated deletion list written to: {consolidated_deletions_path}")

    return {
        "success": failed == 0,
        "total_species": len(results),
        "successful": successful,
        "failed": failed,
        "total_duration": total_duration,
        "report_path": str(report_path),
        "deletion_list_path": str(consolidated_deletions_path),
        "results": results,
    }


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Run image processing pipeline across species directories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all species with deduplication
  %(prog)s /path/to/by_species

  # Process with 4 parallel species workers
  %(prog)s /path/to/by_species --workers 4

  # Process specific species only
  %(prog)s /path/to/by_species --species Acacia_baileyana Acacia_saligna

  # Use stricter duplicate threshold
  %(prog)s /path/to/by_species --threshold 3

  # Dry run to see what would be processed
  %(prog)s /path/to/by_species --dry-run

Available pipeline steps:
  deduplicate  - Detect and mark duplicate images (default)
  validate     - Validate image integrity (placeholder)
  resize       - Resize images to standard dimensions (placeholder)
        """,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Base directory containing species subdirectories",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for output files (default: species directories)",
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=1,
        help="Number of species to process in parallel (default: 1)",
    )

    parser.add_argument(
        "--species",
        nargs="+",
        default=None,
        help="Specific species names to process (default: all)",
    )

    parser.add_argument(
        "--steps",
        nargs="+",
        default=["deduplicate"],
        help="Pipeline steps to run in order (default: deduplicate)",
    )

    # Deduplication options
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=5,
        help="Hamming distance threshold for duplicates (default: 5)",
    )

    parser.add_argument(
        "--hash-size",
        type=int,
        default=16,
        help="Hash size for perceptual hashing (default: 16)",
    )

    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use MD5 file hash for exact duplicate detection only",
    )

    parser.add_argument(
        "--hash-workers",
        type=int,
        default=None,
        help="Workers for parallel hashing within species (default: CPU count)",
    )

    # General options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing",
    )

    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress detailed progress output"
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Create output directory if specified
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # Build configuration
    config = PipelineConfig(
        dedup_hash_size=args.hash_size,
        dedup_hamming_threshold=args.threshold,
        dedup_use_file_hash=args.exact,
        dedup_max_workers=args.hash_workers,
        output_dir=args.output_dir,
        verbose=not args.quiet and args.workers == 1,
        steps=args.steps,
    )

    # Run pipeline
    result = run_pipeline(
        base_dir=args.directory,
        config=config,
        species_filter=args.species,
        max_parallel_species=args.workers,
        dry_run=args.dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
