#!/usr/bin/env python3
"""
Web-based Duplicate Image Review Tool

A local web server that provides a visual interface for reviewing duplicate
image groups detected by the deduplication system. Useful for:
- Verifying that detected duplicates are actually similar
- Tuning threshold values for perceptual hashing
- Reviewing deduplication results before deletion

Usage:
    python review_duplicates.py /path/to/by_species
    python review_duplicates.py /path/to/by_species --port 8080
    python review_duplicates.py /path/to/by_species --threshold 3 --rescan

Then open http://localhost:8000 in your browser.

Dependencies:
    pip install Pillow imagehash
"""

import argparse
import http.server
import json
import mimetypes
import os
import socketserver
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import deduplication module
try:
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        IMAGE_EXTENSIONS,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from deduplicate_images import (
        DEFAULT_HAMMING_THRESHOLD,
        DEFAULT_HASH_SIZE,
        IMAGE_EXTENSIONS,
        compute_image_hash,
        find_duplicate_groups,
        get_image_files,
        select_images_to_keep,
    )


# Global configuration
BASE_DIR: Optional[Path] = None
CURRENT_CONFIG: Dict[str, Any] = {
    "hash_size": DEFAULT_HASH_SIZE,
    "hamming_threshold": DEFAULT_HAMMING_THRESHOLD,
}

# Cache for computed hashes
HASH_CACHE: Dict[str, Dict[Path, str]] = {}


def get_species_list() -> List[str]:
    """Get list of species directories."""
    if BASE_DIR is None:
        return []

    species = []
    for item in sorted(BASE_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has images
            image_count = len(get_image_files(item))
            if image_count > 0:
                species.append(item.name)

    return species


def get_species_duplicates(
    species_name: str, hash_size: int, hamming_threshold: int
) -> Dict[str, Any]:
    """
    Get duplicate groups for a species.

    Returns dict with duplicate group information.
    """
    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_dir = BASE_DIR / species_name
    if not species_dir.exists():
        return {"error": f"Species directory not found: {species_name}"}

    image_files = get_image_files(species_dir)

    if len(image_files) < 2:
        return {
            "species_name": species_name,
            "total_images": len(image_files),
            "duplicate_groups": [],
            "message": "Not enough images for duplicate detection",
        }

    # Check cache
    cache_key = f"{species_name}_{hash_size}"
    if cache_key not in HASH_CACHE:
        # Compute hashes
        hash_map: Dict[Path, str] = {}
        errors = []

        for img_path in image_files:
            result = compute_image_hash(img_path, hash_size, True)
            if result:
                path, img_hash, error = result
                if error:
                    errors.append({"file": path.name, "error": error})
                elif img_hash:
                    hash_map[path] = img_hash

        HASH_CACHE[cache_key] = hash_map
    else:
        hash_map = HASH_CACHE[cache_key]

    # Find duplicate groups with current threshold
    duplicate_groups = find_duplicate_groups(hash_map, hamming_threshold)

    # Format results
    groups = []
    for i, group in enumerate(duplicate_groups, 1):
        keep, delete = select_images_to_keep(group)

        group_info = {
            "group_id": i,
            "keep": {
                "filename": keep.name,
                "size": keep.stat().st_size,
                "path": f"/image/{species_name}/{keep.name}",
            },
            "duplicates": [
                {
                    "filename": p.name,
                    "size": p.stat().st_size,
                    "path": f"/image/{species_name}/{p.name}",
                }
                for p in delete
            ],
            "total_in_group": len(group),
        }
        groups.append(group_info)

    return {
        "species_name": species_name,
        "total_images": len(image_files),
        "hashed_images": len(hash_map),
        "duplicate_groups": groups,
        "total_duplicates": sum(len(g["duplicates"]) for g in groups),
        "hash_size": hash_size,
        "hamming_threshold": hamming_threshold,
    }


def get_all_species_duplicates(
    hash_size: int, hamming_threshold: int
) -> Dict[str, Any]:
    """
    Get duplicate groups for ALL species.

    Returns dict with duplicate group information for every species.
    """
    if BASE_DIR is None:
        return {"error": "Base directory not configured"}

    species_list = get_species_list()

    all_results = []
    total_images = 0
    total_duplicates = 0
    total_groups = 0
    species_with_duplicates = 0

    for species_name in species_list:
        result = get_species_duplicates(species_name, hash_size, hamming_threshold)

        if "error" not in result:
            total_images += result.get("total_images", 0)
            species_duplicates = result.get("total_duplicates", 0)
            total_duplicates += species_duplicates
            total_groups += len(result.get("duplicate_groups", []))

            if species_duplicates > 0:
                species_with_duplicates += 1
                all_results.append(result)

    return {
        "mode": "all_species",
        "total_species_scanned": len(species_list),
        "species_with_duplicates": species_with_duplicates,
        "total_images": total_images,
        "total_duplicates": total_duplicates,
        "total_groups": total_groups,
        "hash_size": hash_size,
        "hamming_threshold": hamming_threshold,
        "species_results": all_results,
    }


def delete_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Delete the specified files.

    Args:
        file_paths: List of relative paths like "species_name/filename.jpg"

    Returns:
        Dict with deletion results
    """
    if BASE_DIR is None:
        return {"success": False, "error": "Base directory not configured"}

    deleted = []
    errors = []

    for rel_path in file_paths:
        try:
            # Security: validate path
            full_path = (BASE_DIR / rel_path).resolve()
            if not full_path.is_relative_to(BASE_DIR.resolve()):
                errors.append({"path": rel_path, "error": "Invalid path"})
                continue

            if not full_path.exists():
                errors.append({"path": rel_path, "error": "File not found"})
                continue

            # Delete the file
            full_path.unlink()
            deleted.append(rel_path)
            print(f"Deleted: {rel_path}")

        except Exception as e:
            errors.append({"path": rel_path, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "deleted_count": len(deleted),
        "deleted": deleted,
        "error_count": len(errors),
        "errors": errors,
    }


def generate_html_page() -> str:
    """Generate the main HTML page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Duplicate Image Review</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: #16213e;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        h1 {
            color: #e94560;
            margin-bottom: 10px;
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: flex-end;
            margin-top: 15px;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .control-group label {
            font-size: 12px;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        select, input[type="number"], button {
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }

        select, input[type="number"] {
            background: #0f3460;
            color: #fff;
            min-width: 200px;
        }

        select:focus, input[type="number"]:focus {
            outline: 2px solid #e94560;
        }

        button {
            background: #e94560;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s, transform 0.1s;
        }

        button:hover {
            background: #ff6b6b;
        }

        button:active {
            transform: scale(0.98);
        }

        button:disabled {
            background: #555;
            cursor: not-allowed;
            transform: none;
        }

        button.secondary {
            background: #0f3460;
        }

        button.secondary:hover {
            background: #1a4a7a;
        }

        button.secondary.active {
            background: #4ecca3;
            color: #000;
        }

        button.confirm-btn {
            background: #4ecca3;
            color: #000;
            font-size: 12px;
            padding: 6px 12px;
        }

        button.confirm-btn:hover {
            background: #3db892;
        }

        button.confirm-btn.confirmed {
            background: #2d8a6e;
            color: #fff;
        }

        button.delete-btn {
            background: #dc3545;
        }

        button.delete-btn:hover {
            background: #c82333;
        }

        .mode-buttons {
            display: flex;
            gap: 10px;
        }

        .action-bar {
            background: #0f3460;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .action-bar-left {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .action-bar-right {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .confirmed-count {
            background: #4ecca3;
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }

        .stats {
            background: #16213e;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #e94560;
        }

        .stat-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }

        .loading {
            text-align: center;
            padding: 50px;
            color: #888;
        }

        .spinner {
            border: 4px solid #333;
            border-top: 4px solid #e94560;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .species-section {
            margin-bottom: 30px;
        }

        .species-section.collapsed .species-groups {
            display: none;
        }

        .species-section.collapsed .species-header {
            border-radius: 10px;
        }

        .species-groups {
            transition: max-height 0.3s ease;
        }

        .species-header {
            background: #e94560;
            color: white;
            padding: 15px 20px;
            border-radius: 10px 10px 0 0;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            cursor: pointer;
            user-select: none;
            transition: border-radius 0.2s;
        }

        .species-header:hover {
            filter: brightness(1.1);
        }

        .species-header.confirmed {
            background: #2d8a6e;
        }

        .species-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .collapse-indicator {
            font-size: 14px;
            transition: transform 0.2s;
            display: inline-block;
            margin-right: 8px;
        }

        .species-section.collapsed .collapse-indicator {
            transform: rotate(-90deg);
        }

        .species-header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .species-stats {
            font-size: 14px;
            font-weight: normal;
            opacity: 0.9;
        }

        .duplicate-group {
            background: #16213e;
            border-radius: 10px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: border-color 0.2s;
            border: 2px solid transparent;
        }

        .duplicate-group.confirmed {
            border-color: #4ecca3;
        }

        .species-section .duplicate-group:first-of-type {
            border-radius: 0 0 10px 10px;
            margin-top: 0;
        }

        .species-section .duplicate-group {
            border-radius: 10px;
            margin-top: 10px;
        }

        .group-header {
            background: #0f3460;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .group-header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .group-title {
            font-weight: bold;
            color: #e94560;
        }

        .group-count {
            background: #e94560;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
        }

        .images-container {
            display: flex;
            flex-wrap: wrap;
            padding: 15px;
            gap: 15px;
        }

        .image-card {
            background: #0f3460;
            border-radius: 8px;
            overflow: hidden;
            width: 250px;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .image-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
        }

        .image-card.keep {
            border: 3px solid #4ecca3;
        }

        .image-card.duplicate {
            border: 3px solid #e94560;
        }

        .image-wrapper {
            width: 100%;
            height: 200px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
            cursor: pointer;
        }

        .image-wrapper img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        .image-info {
            padding: 10px;
        }

        .image-filename {
            font-size: 12px;
            color: #ddd;
            word-break: break-all;
            margin-bottom: 5px;
        }

        .image-size {
            font-size: 11px;
            color: #888;
        }

        .image-status {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            margin-top: 5px;
        }

        .status-keep {
            background: #4ecca3;
            color: #000;
        }

        .status-delete {
            background: #e94560;
            color: #fff;
        }

        .no-duplicates {
            text-align: center;
            padding: 50px;
            color: #4ecca3;
            font-size: 18px;
        }

        .error {
            background: #e94560;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .success-message {
            background: #4ecca3;
            color: #000;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: bold;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .modal.active {
            display: flex;
        }

        .modal img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
        }

        .modal-close {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            color: white;
            cursor: pointer;
        }

        /* Confirmation modal */
        .confirm-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1001;
            justify-content: center;
            align-items: center;
        }

        .confirm-modal.active {
            display: flex;
        }

        .confirm-modal-content {
            background: #16213e;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }

        .confirm-modal-content h2 {
            color: #e94560;
            margin-bottom: 15px;
        }

        .confirm-modal-content p {
            margin-bottom: 20px;
            line-height: 1.6;
        }

        .confirm-modal-content .warning-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }

        .confirm-modal-content .file-count {
            font-size: 36px;
            font-weight: bold;
            color: #e94560;
            margin: 10px 0;
        }

        .confirm-modal-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
        }

        .confirm-modal-buttons button {
            min-width: 120px;
        }

        .threshold-info {
            background: #0f3460;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 12px;
            color: #aaa;
            margin-top: 10px;
        }

        .threshold-info strong {
            color: #e94560;
        }

        .warning-banner {
            background: #ff9800;
            color: #000;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: bold;
        }

        .checkmark {
            color: #4ecca3;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌿 Duplicate Image Review</h1>
            <p>Visual review tool for tuning deduplication parameters</p>

            <div class="controls">
                <div class="control-group">
                    <label>View Mode</label>
                    <div class="mode-buttons">
                        <button id="singleModeBtn" class="secondary active" onclick="setMode('single')">Single Species</button>
                        <button id="allModeBtn" class="secondary" onclick="setMode('all')">All Species</button>
                    </div>
                </div>

                <div class="control-group" id="speciesSelectGroup">
                    <label>Species</label>
                    <select id="speciesSelect">
                        <option value="">Loading species...</option>
                    </select>
                </div>

                <div class="control-group">
                    <label>Hash Size</label>
                    <input type="number" id="hashSize" value="16" min="4" max="32" step="2">
                </div>

                <div class="control-group">
                    <label>Hamming Threshold</label>
                    <input type="number" id="hammingThreshold" value="5" min="0" max="20">
                </div>

                <div class="control-group">
                    <label>&nbsp;</label>
                    <button id="analyzeBtn" onclick="analyzeDuplicates()">Analyze</button>
                </div>
            </div>

            <div class="threshold-info">
                <strong>Hamming Threshold:</strong> Lower values = stricter matching (fewer false positives).
                Higher values = more permissive (may catch more duplicates but also false positives).
                <br>
                <strong>Hash Size:</strong> Higher values = more precise hashing but slower computation.
            </div>
        </header>

        <div class="action-bar" id="actionBar" style="display: none;">
            <div class="action-bar-left">
                <span class="confirmed-count" id="confirmedCount">0 groups confirmed</span>
                <button class="confirm-btn" onclick="confirmAll()">✓ Confirm All</button>
                <button class="secondary" onclick="resetConfirmations()">Reset</button>
                <button class="secondary" onclick="collapseAllSpecies()">Collapse All</button>
                <button class="secondary" onclick="expandAllSpecies()">Expand All</button>
            </div>
            <div class="action-bar-right">
                <button class="delete-btn" id="deleteBtn" onclick="showDeleteModal()" disabled>
                    🗑️ Delete Confirmed Duplicates
                </button>
            </div>
        </div>

        <div class="stats" id="stats" style="display: none;">
            <div class="stat" id="speciesScannedStat" style="display: none;">
                <div class="stat-value" id="speciesScanned">0</div>
                <div class="stat-label">Species Scanned</div>
            </div>
            <div class="stat" id="speciesWithDupsStat" style="display: none;">
                <div class="stat-value" id="speciesWithDups">0</div>
                <div class="stat-label">Species with Duplicates</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="totalImages">0</div>
                <div class="stat-label">Total Images</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="duplicateGroups">0</div>
                <div class="stat-label">Duplicate Groups</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="totalDuplicates">0</div>
                <div class="stat-label">Marked for Deletion</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="uniqueImages">0</div>
                <div class="stat-label">Unique Images</div>
            </div>
        </div>

        <div id="content">
            <div class="loading" id="initialMessage">
                <p>Select a species and click "Analyze" to begin reviewing duplicates.</p>
                <p style="margin-top: 10px; font-size: 14px; color: #666;">
                    Or switch to "All Species" mode to scan the entire dataset.
                </p>
            </div>
        </div>
    </div>

    <!-- Image preview modal -->
    <div class="modal" id="imageModal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="Full size image">
    </div>

    <!-- Confirm All modal -->
    <div class="confirm-modal" id="confirmAllModal">
        <div class="confirm-modal-content">
            <div class="warning-icon">⚠️</div>
            <h2>Confirm All Groups</h2>
            <p>You are about to confirm <strong id="confirmAllCount">0</strong> duplicate groups for deletion.</p>
            <p>This will mark <strong id="confirmAllFiles">0</strong> files for deletion.</p>
            <p style="color: #aaa; font-size: 14px;">Files will not be deleted until you click the delete button.</p>
            <div class="confirm-modal-buttons">
                <button class="secondary" onclick="hideConfirmAllModal()">Cancel</button>
                <button class="confirm-btn" onclick="doConfirmAll()">Confirm All</button>
            </div>
        </div>
    </div>

    <!-- Delete confirmation modal -->
    <div class="confirm-modal" id="deleteModal">
        <div class="confirm-modal-content">
            <div class="warning-icon">🗑️</div>
            <h2>Delete Confirmed Duplicates</h2>
            <p style="color: #e94560; font-weight: bold;">This action cannot be undone!</p>
            <div class="file-count" id="deleteFileCount">0</div>
            <p>files will be permanently deleted</p>
            <p style="color: #aaa; font-size: 14px; margin-top: 15px;">
                Only files in confirmed groups will be deleted.<br>
                The highest quality image from each group will be kept.
            </p>
            <div class="confirm-modal-buttons">
                <button class="secondary" onclick="hideDeleteModal()">Cancel</button>
                <button class="delete-btn" onclick="executeDelete()">Delete Files</button>
            </div>
        </div>
    </div>

    <script>
        let currentMode = 'single';
        let currentData = null;
        let confirmedGroups = new Set(); // Format: "speciesName:groupId"

        // Load species list on page load
        document.addEventListener('DOMContentLoaded', loadSpecies);

        function setMode(mode) {
            currentMode = mode;
            confirmedGroups.clear();
            updateConfirmedCount();

            document.getElementById('singleModeBtn').classList.toggle('active', mode === 'single');
            document.getElementById('allModeBtn').classList.toggle('active', mode === 'all');
            document.getElementById('speciesSelectGroup').style.display = mode === 'single' ? 'flex' : 'none';

            if (mode === 'all') {
                document.getElementById('initialMessage').innerHTML = `
                    <p>Click "Analyze" to scan ALL species for duplicates.</p>
                    <p style="margin-top: 10px; font-size: 14px; color: #ff9800;">
                        ⚠️ This may take several minutes depending on the number of species and images.
                    </p>
                `;
            } else {
                document.getElementById('initialMessage').innerHTML = `
                    <p>Select a species and click "Analyze" to begin reviewing duplicates.</p>
                    <p style="margin-top: 10px; font-size: 14px; color: #666;">
                        Or switch to "All Species" mode to scan the entire dataset.
                    </p>
                `;
            }
        }

        async function loadSpecies() {
            try {
                const response = await fetch('/api/species');
                const species = await response.json();

                const select = document.getElementById('speciesSelect');
                select.innerHTML = '<option value="">-- Select a species --</option>';

                species.forEach(name => {
                    const option = document.createElement('option');
                    option.value = name;
                    option.textContent = name.replace(/_/g, ' ');
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Failed to load species:', error);
                document.getElementById('speciesSelect').innerHTML =
                    '<option value="">Error loading species</option>';
            }
        }

        async function analyzeDuplicates() {
            confirmedGroups.clear();
            updateConfirmedCount();

            if (currentMode === 'single') {
                await analyzeSingleSpecies();
            } else {
                await analyzeAllSpecies();
            }
        }

        async function analyzeSingleSpecies() {
            const species = document.getElementById('speciesSelect').value;
            if (!species) {
                alert('Please select a species first');
                return;
            }

            const hashSize = document.getElementById('hashSize').value;
            const threshold = document.getElementById('hammingThreshold').value;

            document.getElementById('content').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing images for ${species.replace(/_/g, ' ')}...</p>
                </div>
            `;
            document.getElementById('stats').style.display = 'none';
            document.getElementById('actionBar').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;

            try {
                const response = await fetch(
                    `/api/duplicates/${species}?hash_size=${hashSize}&threshold=${threshold}`
                );
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                currentData = { mode: 'single', species_results: [data] };
                displaySingleSpeciesResults(data);
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            } finally {
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        async function analyzeAllSpecies() {
            const hashSize = document.getElementById('hashSize').value;
            const threshold = document.getElementById('hammingThreshold').value;

            document.getElementById('content').innerHTML = `
                <div class="warning-banner">
                    ⚠️ Scanning all species - this may take several minutes. Please wait...
                </div>
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing images across all species...</p>
                </div>
            `;
            document.getElementById('stats').style.display = 'none';
            document.getElementById('actionBar').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;

            try {
                const response = await fetch(
                    `/api/duplicates/all?hash_size=${hashSize}&threshold=${threshold}`
                );
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                currentData = data;
                displayAllSpeciesResults(data);
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            } finally {
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        function displaySingleSpeciesResults(data) {
            document.getElementById('speciesScannedStat').style.display = 'none';
            document.getElementById('speciesWithDupsStat').style.display = 'none';
            document.getElementById('stats').style.display = 'flex';
            document.getElementById('totalImages').textContent = data.total_images;
            document.getElementById('duplicateGroups').textContent = data.duplicate_groups.length;
            document.getElementById('totalDuplicates').textContent = data.total_duplicates;
            document.getElementById('uniqueImages').textContent = data.total_images - data.total_duplicates;

            const content = document.getElementById('content');

            if (data.duplicate_groups.length === 0) {
                document.getElementById('actionBar').style.display = 'none';
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No duplicate images found with current settings.<br>
                        <small>Try increasing the Hamming threshold to detect more similar images.</small>
                    </div>
                `;
                return;
            }

            document.getElementById('actionBar').style.display = 'flex';
            let html = '';
            data.duplicate_groups.forEach(group => {
                html += renderDuplicateGroup(data.species_name, group);
            });
            content.innerHTML = html;
        }

        function displayAllSpeciesResults(data) {
            document.getElementById('speciesScannedStat').style.display = 'block';
            document.getElementById('speciesWithDupsStat').style.display = 'block';
            document.getElementById('stats').style.display = 'flex';
            document.getElementById('speciesScanned').textContent = data.total_species_scanned;
            document.getElementById('speciesWithDups').textContent = data.species_with_duplicates;
            document.getElementById('totalImages').textContent = data.total_images;
            document.getElementById('duplicateGroups').textContent = data.total_groups;
            document.getElementById('totalDuplicates').textContent = data.total_duplicates;
            document.getElementById('uniqueImages').textContent = data.total_images - data.total_duplicates;

            const content = document.getElementById('content');

            if (data.species_results.length === 0) {
                document.getElementById('actionBar').style.display = 'none';
                content.innerHTML = `
                    <div class="no-duplicates">
                        ✓ No duplicate images found across any species with current settings.<br>
                        <small>Try increasing the Hamming threshold to detect more similar images.</small>
                    </div>
                `;
                return;
            }

            document.getElementById('actionBar').style.display = 'flex';
            let html = '';
            data.species_results.forEach(speciesData => {
                const speciesKey = speciesData.species_name;
                const allConfirmed = speciesData.duplicate_groups.every(g =>
                    confirmedGroups.has(`${speciesKey}:${g.group_id}`)
                );
                html += `
                    <div class="species-section" id="species-${speciesKey}">
                        <div class="species-header ${allConfirmed ? 'confirmed' : ''}" id="species-header-${speciesKey}" onclick="toggleSpeciesCollapse('${speciesKey}')">
                            <div class="species-header-left">
                                <span><span class="collapse-indicator">▼</span>${allConfirmed ? '<span class="checkmark">✓</span>' : ''}🌿 ${speciesData.species_name.replace(/_/g, ' ')}</span>
                            </div>
                            <div class="species-header-right">
                                <span class="species-stats">
                                    ${speciesData.duplicate_groups.length} groups ·
                                    ${speciesData.total_duplicates} duplicates
                                </span>
                                <button class="confirm-btn ${allConfirmed ? 'confirmed' : ''}"
                                        onclick="event.stopPropagation(); confirmSpecies('${speciesKey}')">
                                    ${allConfirmed ? '✓ Confirmed' : 'Confirm Species'}
                                </button>
                            </div>
                        </div>
                        <div class="species-groups" id="species-groups-${speciesKey}">
                `;
                speciesData.duplicate_groups.forEach(group => {
                    html += renderDuplicateGroup(speciesData.species_name, group);
                });
                html += '</div></div>';
            });
            content.innerHTML = html;
        }

        function renderDuplicateGroup(speciesName, group) {
            const groupKey = `${speciesName}:${group.group_id}`;
            const isConfirmed = confirmedGroups.has(groupKey);
            return `
                <div class="duplicate-group ${isConfirmed ? 'confirmed' : ''}" id="group-${groupKey.replace(':', '-')}">
                    <div class="group-header">
                        <div class="group-header-left">
                            <span class="group-title">${isConfirmed ? '<span class="checkmark">✓</span>' : ''}Group ${group.group_id}</span>
                            <span class="group-count">${group.total_in_group} images</span>
                        </div>
                        <button class="confirm-btn ${isConfirmed ? 'confirmed' : ''}"
                                onclick="confirmGroup('${speciesName}', ${group.group_id})">
                            ${isConfirmed ? '✓ Confirmed' : 'Confirm'}
                        </button>
                    </div>
                    <div class="images-container">
                        <div class="image-card keep">
                            <div class="image-wrapper" onclick="showModal('${group.keep.path}')">
                                <img src="${group.keep.path}" alt="${group.keep.filename}" loading="lazy">
                            </div>
                            <div class="image-info">
                                <div class="image-filename">${group.keep.filename}</div>
                                <div class="image-size">${formatSize(group.keep.size)}</div>
                                <span class="image-status status-keep">Keep</span>
                            </div>
                        </div>
                        ${group.duplicates.map(dup => `
                            <div class="image-card duplicate">
                                <div class="image-wrapper" onclick="showModal('${dup.path}')">
                                    <img src="${dup.path}" alt="${dup.filename}" loading="lazy">
                                </div>
                                <div class="image-info">
                                    <div class="image-filename">${dup.filename}</div>
                                    <div class="image-size">${formatSize(dup.size)}</div>
                                    <span class="image-status status-delete">Delete</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function confirmGroup(speciesName, groupId) {
            const groupKey = `${speciesName}:${groupId}`;
            if (confirmedGroups.has(groupKey)) {
                confirmedGroups.delete(groupKey);
            } else {
                confirmedGroups.add(groupKey);
            }
            updateGroupUI(speciesName, groupId);
            updateSpeciesUI(speciesName);
            updateConfirmedCount();
        }

        function confirmSpecies(speciesName) {
            if (!currentData) return;
            const speciesData = currentData.species_results.find(s => s.species_name === speciesName);
            if (!speciesData) return;

            const allConfirmed = speciesData.duplicate_groups.every(g =>
                confirmedGroups.has(`${speciesName}:${g.group_id}`)
            );

            speciesData.duplicate_groups.forEach(group => {
                const groupKey = `${speciesName}:${group.group_id}`;
                if (allConfirmed) {
                    confirmedGroups.delete(groupKey);
                } else {
                    confirmedGroups.add(groupKey);
                }
                updateGroupUI(speciesName, group.group_id);
            });
            updateSpeciesUI(speciesName);
            updateConfirmedCount();
        }

        function toggleSpeciesCollapse(speciesName) {
            const section = document.getElementById(`species-${speciesName}`);
            if (section) {
                section.classList.toggle('collapsed');
            }
        }

        function collapseAllSpecies() {
            document.querySelectorAll('.species-section').forEach(section => {
                section.classList.add('collapsed');
            });
        }

        function expandAllSpecies() {
            document.querySelectorAll('.species-section').forEach(section => {
                section.classList.remove('collapsed');
            });
        }

        function confirmAll() {
            if (!currentData) return;
            let totalGroups = 0;
            let totalFiles = 0;
            currentData.species_results.forEach(species => {
                species.duplicate_groups.forEach(group => {
                    totalGroups++;
                    totalFiles += group.duplicates.length;
                });
            });
            document.getElementById('confirmAllCount').textContent = totalGroups;
            document.getElementById('confirmAllFiles').textContent = totalFiles;
            document.getElementById('confirmAllModal').classList.add('active');
        }

        function hideConfirmAllModal() {
            document.getElementById('confirmAllModal').classList.remove('active');
        }

        function doConfirmAll() {
            if (!currentData) return;
            currentData.species_results.forEach(species => {
                species.duplicate_groups.forEach(group => {
                    confirmedGroups.add(`${species.species_name}:${group.group_id}`);
                    updateGroupUI(species.species_name, group.group_id);
                });
                updateSpeciesUI(species.species_name);
            });
            updateConfirmedCount();
            hideConfirmAllModal();
        }

        function resetConfirmations() {
            confirmedGroups.clear();
            if (currentData) {
                currentData.species_results.forEach(species => {
                    species.duplicate_groups.forEach(group => {
                        updateGroupUI(species.species_name, group.group_id);
                    });
                    updateSpeciesUI(species.species_name);
                });
            }
            updateConfirmedCount();
        }

        function updateGroupUI(speciesName, groupId) {
            const groupKey = `${speciesName}:${groupId}`;
            const isConfirmed = confirmedGroups.has(groupKey);
            const groupEl = document.getElementById(`group-${groupKey.replace(':', '-')}`);
            if (groupEl) {
                groupEl.classList.toggle('confirmed', isConfirmed);
                const btn = groupEl.querySelector('.confirm-btn');
                if (btn) {
                    btn.classList.toggle('confirmed', isConfirmed);
                    btn.innerHTML = isConfirmed ? '✓ Confirmed' : 'Confirm';
                }
                const title = groupEl.querySelector('.group-title');
                if (title) {
                    title.innerHTML = isConfirmed ? `<span class="checkmark">✓</span>Group ${groupId}` : `Group ${groupId}`;
                }
            }
        }

        function updateSpeciesUI(speciesName) {
            if (!currentData) return;
            const speciesData = currentData.species_results.find(s => s.species_name === speciesName);
            if (!speciesData) return;

            const allConfirmed = speciesData.duplicate_groups.every(g =>
                confirmedGroups.has(`${speciesName}:${g.group_id}`)
            );
            const headerEl = document.getElementById(`species-header-${speciesName}`);
            if (headerEl) {
                headerEl.classList.toggle('confirmed', allConfirmed);
                const btn = headerEl.querySelector('.confirm-btn');
                if (btn) {
                    btn.classList.toggle('confirmed', allConfirmed);
                    btn.innerHTML = allConfirmed ? '✓ Confirmed' : 'Confirm Species';
                }
                const leftSpan = headerEl.querySelector('.species-header-left span');
                if (leftSpan) {
                    leftSpan.innerHTML = `<span class="collapse-indicator">▼</span>${allConfirmed ? '<span class="checkmark">✓</span>' : ''}🌿 ${speciesName.replace(/_/g, ' ')}`;
                }
            }
        }

        function updateConfirmedCount() {
            const count = confirmedGroups.size;
            document.getElementById('confirmedCount').textContent = `${count} group${count !== 1 ? 's' : ''} confirmed`;
            document.getElementById('deleteBtn').disabled = count === 0;
        }

        function getConfirmedFilePaths() {
            if (!currentData) return [];
            const paths = [];
            currentData.species_results.forEach(species => {
                species.duplicate_groups.forEach(group => {
                    if (confirmedGroups.has(`${species.species_name}:${group.group_id}`)) {
                        group.duplicates.forEach(dup => {
                            paths.push(`${species.species_name}/${dup.filename}`);
                        });
                    }
                });
            });
            return paths;
        }

        function showDeleteModal() {
            const paths = getConfirmedFilePaths();
            document.getElementById('deleteFileCount').textContent = paths.length;
            document.getElementById('deleteModal').classList.add('active');
        }

        function hideDeleteModal() {
            document.getElementById('deleteModal').classList.remove('active');
        }

        async function executeDelete() {
            const paths = getConfirmedFilePaths();
            if (paths.length === 0) {
                hideDeleteModal();
                return;
            }

            hideDeleteModal();
            document.getElementById('content').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Deleting ${paths.length} files...</p>
                </div>
            `;

            try {
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: paths })
                });
                const result = await response.json();

                if (result.success) {
                    document.getElementById('content').innerHTML = `
                        <div class="success-message">
                            ✓ Successfully deleted ${result.deleted_count} files
                        </div>
                        <p style="text-align: center; margin-top: 20px;">
                            Click "Analyze" to refresh the results.
                        </p>
                    `;
                } else {
                    document.getElementById('content').innerHTML = `
                        <div class="success-message">
                            ✓ Deleted ${result.deleted_count} files
                        </div>
                        <div class="error">
                            ${result.error_count} files could not be deleted.
                        </div>
                    `;
                }
                confirmedGroups.clear();
                updateConfirmedCount();
                document.getElementById('actionBar').style.display = 'none';
                document.getElementById('stats').style.display = 'none';
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            }
        }

        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }

        function showModal(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('active');
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal();
                hideConfirmAllModal();
                hideDeleteModal();
            }
        });

        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') analyzeDuplicates();
            });
        });
    </script>
</body>
</html>
"""


class DuplicateReviewHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the duplicate review server."""

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_html(self, content: str, status: int = 200):
        """Send HTML response."""
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_image(self, filepath: Path):
        """Send image file."""
        if not filepath.exists():
            self.send_error(404, "Image not found")
            return

        mime_type, _ = mimetypes.guess_type(str(filepath))
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "max-age=3600")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading image: {e}")

    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_html(generate_html_page())
            return

        if path == "/api/species":
            species = get_species_list()
            self.send_json(species)
            return

        if path == "/api/duplicates/all":
            hash_size = int(query.get("hash_size", [str(DEFAULT_HASH_SIZE)])[0])
            threshold = int(query.get("threshold", [str(DEFAULT_HAMMING_THRESHOLD)])[0])
            result = get_all_species_duplicates(hash_size, threshold)
            self.send_json(result)
            return

        if path.startswith("/api/duplicates/"):
            species_name = urllib.parse.unquote(path[16:])
            hash_size = int(query.get("hash_size", [str(DEFAULT_HASH_SIZE)])[0])
            threshold = int(query.get("threshold", [str(DEFAULT_HAMMING_THRESHOLD)])[0])
            result = get_species_duplicates(species_name, hash_size, threshold)
            self.send_json(result)
            return

        if path.startswith("/image/"):
            parts = path[7:].split("/", 1)
            if len(parts) == 2 and BASE_DIR:
                species_name = urllib.parse.unquote(parts[0])
                filename = urllib.parse.unquote(parts[1])
                image_path = (BASE_DIR / species_name / filename).resolve()
                if image_path.is_relative_to(BASE_DIR.resolve()):
                    self.send_image(image_path)
                    return
            self.send_error(404, "Image not found")
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                files = data.get("files", [])
                result = delete_files(files)
                self.send_json(result)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)
            return

        self.send_error(404, "Not found")


def run_server(base_dir: Path, port: int = 8000):
    """Start the review server."""
    global BASE_DIR
    BASE_DIR = base_dir

    with socketserver.TCPServer(("", port), DuplicateReviewHandler) as httpd:
        print(f"\n{'=' * 60}")
        print(f"🌿 Duplicate Image Review Server")
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
        description="Web-based duplicate image review tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/by_species
  %(prog)s /path/to/by_species --port 8080

Then open http://localhost:8000 in your browser.
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

    args = parser.parse_args()

    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    run_server(args.directory, args.port)


if __name__ == "__main__":
    main()
