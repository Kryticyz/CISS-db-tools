"""
Modern HTML template generation for the duplicate review interface.

This template provides a user-friendly, card-based UI for:
- Finding duplicates, similar images, and outliers
- Selecting images for deletion
- Safe deletion workflow with confirmation
- Support for single species and all species modes
"""


def generate_html_page() -> str:
    """
    Generate the main HTML page with embedded CSS and JavaScript.

    Features:
    - Modern, responsive design
    - Card-based mode selection
    - Collapsible image groups
    - Clear deletion workflow with confirmation
    - Progress tracking
    - Mobile-friendly
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plant Image Review</title>
    <style>
        /* ============================================
           CSS VARIABLES - Design System
           ============================================ */
        :root {
            /* Colors */
            --color-primary: #2563eb;
            --color-success: #10b981;
            --color-warning: #f59e0b;
            --color-danger: #ef4444;
            --color-bg: #f8fafc;
            --color-surface: #ffffff;
            --color-text: #1e293b;
            --color-text-light: #64748b;
            --color-border: #e2e8f0;

            /* Spacing */
            --space-xs: 0.25rem;
            --space-sm: 0.5rem;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;

            /* Borders */
            --radius-sm: 0.375rem;
            --radius-md: 0.5rem;
            --radius-lg: 0.75rem;
            --radius-xl: 1rem;

            /* Shadows */
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        /* ============================================
           RESET & BASE STYLES
           ============================================ */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.5;
            min-height: 100vh;
        }

        /* ============================================
           LAYOUT
           ============================================ */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--space-lg);
        }

        .screen {
            display: none;
        }

        .screen.active {
            display: block;
        }

        /* ============================================
           HEADER
           ============================================ */
        .app-header {
            text-align: center;
            margin-bottom: var(--space-2xl);
            padding: var(--space-xl) 0;
        }

        .app-header h1 {
            font-size: 2rem;
            color: var(--color-text);
            margin-bottom: var(--space-sm);
        }

        .app-header p {
            color: var(--color-text-light);
            font-size: 1.125rem;
        }

        /* ============================================
           MODE SELECTION CARDS
           ============================================ */
        .mode-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: var(--space-lg);
            margin-bottom: var(--space-2xl);
        }

        .mode-card {
            background: var(--color-surface);
            border: 2px solid var(--color-border);
            border-radius: var(--radius-xl);
            padding: var(--space-xl);
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }

        .mode-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
            border-color: var(--color-primary);
        }

        .mode-card-icon {
            font-size: 3rem;
            margin-bottom: var(--space-md);
        }

        .mode-card h3 {
            font-size: 1.25rem;
            margin-bottom: var(--space-sm);
            color: var(--color-text);
        }

        .mode-card p {
            color: var(--color-text-light);
            margin-bottom: var(--space-xs);
        }

        .mode-card small {
            color: var(--color-text-light);
            font-size: 0.875rem;
        }

        /* ============================================
           SCOPE SELECTOR
           ============================================ */
        .scope-selector {
            background: var(--color-surface);
            border-radius: var(--radius-lg);
            padding: var(--space-xl);
            margin-bottom: var(--space-xl);
            box-shadow: var(--shadow-sm);
        }

        .scope-selector h3 {
            margin-bottom: var(--space-md);
            color: var(--color-text);
        }

        .radio-group {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
        }

        .radio-option {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-md);
            border: 2px solid var(--color-border);
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .radio-option:hover {
            border-color: var(--color-primary);
            background: #f1f5f9;
        }

        .radio-option input[type="radio"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .radio-option label {
            cursor: pointer;
            flex: 1;
            font-size: 1rem;
        }

        .species-dropdown {
            margin-top: var(--space-md);
        }

        .species-dropdown select {
            width: 100%;
            padding: var(--space-md);
            border: 2px solid var(--color-border);
            border-radius: var(--radius-md);
            font-size: 1rem;
            background: var(--color-surface);
            color: var(--color-text);
            cursor: pointer;
        }

        .species-dropdown select:focus {
            outline: none;
            border-color: var(--color-primary);
        }

        .species-dropdown select:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* ============================================
           BUTTONS
           ============================================ */
        .btn {
            display: inline-block;
            padding: var(--space-md) var(--space-xl);
            border: none;
            border-radius: var(--radius-md);
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }

        .btn-primary {
            background: var(--color-primary);
            color: white;
        }

        .btn-primary:hover {
            background: #1d4ed8;
        }

        .btn-success {
            background: var(--color-success);
            color: white;
        }

        .btn-success:hover {
            background: #059669;
        }

        .btn-danger {
            background: var(--color-danger);
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .btn-secondary {
            background: #6b7280;
            color: white;
        }

        .btn-secondary:hover {
            background: #4b5563;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-block {
            width: 100%;
        }

        .btn-group {
            display: flex;
            gap: var(--space-md);
            margin-top: var(--space-lg);
        }

        /* ============================================
           RESULTS VIEW
           ============================================ */
        .results-header {
            background: var(--color-surface);
            padding: var(--space-xl);
            border-radius: var(--radius-lg);
            margin-bottom: var(--space-xl);
            box-shadow: var(--shadow-sm);
        }

        .results-header h2 {
            color: var(--color-text);
            margin-bottom: var(--space-sm);
        }

        .results-stats {
            color: var(--color-text-light);
            font-size: 1rem;
        }

        .results-actions {
            margin-top: var(--space-lg);
            display: flex;
            gap: var(--space-md);
            flex-wrap: wrap;
        }

        /* ============================================
           SPECIES SECTIONS
           ============================================ */
        .species-section {
            margin-bottom: var(--space-2xl);
        }

        .species-header {
            background: var(--color-surface);
            padding: var(--space-lg);
            border-radius: var(--radius-lg);
            margin-bottom: var(--space-md);
            box-shadow: var(--shadow-sm);
        }

        .species-header h3 {
            color: var(--color-text);
            font-size: 1.5rem;
            margin-bottom: var(--space-xs);
        }

        .species-header p {
            color: var(--color-text-light);
        }

        /* ============================================
           IMAGE GROUPS
           ============================================ */
        .image-group {
            background: var(--color-surface);
            border: 2px solid var(--color-border);
            border-radius: var(--radius-lg);
            margin-bottom: var(--space-lg);
            overflow: hidden;
        }

        .group-header {
            padding: var(--space-lg);
            background: #f8fafc;
            border-bottom: 2px solid var(--color-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }

        .group-header:hover {
            background: #f1f5f9;
        }

        .group-title {
            font-weight: 600;
            color: var(--color-text);
        }

        .group-actions {
            display: flex;
            gap: var(--space-sm);
        }

        .group-content {
            padding: var(--space-lg);
            display: none;
        }

        .group-content.expanded {
            display: block;
        }

        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: var(--space-lg);
        }

        /* ============================================
           IMAGE ITEMS
           ============================================ */
        .image-item {
            position: relative;
            border: 3px solid var(--color-border);
            border-radius: var(--radius-md);
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s ease;
            background: var(--color-surface);
        }

        .image-item:hover {
            box-shadow: var(--shadow-md);
        }

        .image-item.selected {
            border-color: var(--color-danger);
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
        }

        .image-item.keep {
            border-color: var(--color-success);
        }

        .image-wrapper {
            position: relative;
            width: 100%;
            padding-top: 75%; /* 4:3 aspect ratio */
            background: #f1f5f9;
        }

        .image-wrapper img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .image-checkbox {
            position: absolute;
            top: var(--space-sm);
            right: var(--space-sm);
            width: 32px;
            height: 32px;
            background: white;
            border: 2px solid var(--color-border);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: var(--shadow-md);
            z-index: 10;
        }

        .image-item.selected .image-checkbox {
            background: var(--color-danger);
            border-color: var(--color-danger);
            color: white;
        }

        .image-info {
            padding: var(--space-md);
        }

        .image-filename {
            font-size: 0.875rem;
            color: var(--color-text);
            margin-bottom: var(--space-xs);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .image-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--color-text-light);
        }

        .size-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            font-weight: 600;
        }

        .size-badge.largest {
            background: #d1fae5;
            color: #065f46;
        }

        .size-badge.smaller {
            background: #fef3c7;
            color: #92400e;
        }

        /* ============================================
           STICKY FOOTER
           ============================================ */
        .sticky-footer {
            position: sticky;
            bottom: 0;
            background: var(--color-surface);
            border-top: 2px solid var(--color-border);
            padding: var(--space-lg);
            box-shadow: 0 -4px 6px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: var(--space-2xl);
        }

        .selection-count {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--color-text);
        }

        .footer-actions {
            display: flex;
            gap: var(--space-md);
        }

        /* ============================================
           MODALS
           ============================================ */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: var(--space-lg);
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: var(--color-surface);
            border-radius: var(--radius-lg);
            padding: var(--space-2xl);
            max-width: 600px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }

        .modal-header {
            display: flex;
            align-items: center;
            margin-bottom: var(--space-xl);
        }

        .modal-icon {
            font-size: 2.5rem;
            margin-right: var(--space-md);
        }

        .modal-header h2 {
            color: var(--color-text);
            font-size: 1.5rem;
        }

        .modal-body {
            margin-bottom: var(--space-xl);
        }

        .deletion-summary {
            background: #fef2f2;
            border: 2px solid var(--color-danger);
            border-radius: var(--radius-md);
            padding: var(--space-xl);
            margin: var(--space-lg) 0;
            text-align: center;
        }

        .deletion-summary-stat {
            font-size: 2rem;
            font-weight: bold;
            color: var(--color-danger);
            margin-bottom: var(--space-sm);
        }

        .deletion-summary-label {
            color: var(--color-text-light);
            font-size: 0.875rem;
        }

        .warning-message {
            background: #fef3c7;
            border-left: 4px solid var(--color-warning);
            padding: var(--space-md);
            margin: var(--space-lg) 0;
            border-radius: var(--radius-sm);
        }

        .file-list {
            max-height: 200px;
            overflow-y: auto;
            background: #f8fafc;
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-top: var(--space-md);
        }

        .file-list-item {
            padding: var(--space-xs);
            font-size: 0.875rem;
            color: var(--color-text-light);
        }

        .modal-actions {
            display: flex;
            gap: var(--space-md);
            justify-content: flex-end;
        }

        /* ============================================
           PROGRESS
           ============================================ */
        .progress-container {
            margin: var(--space-lg) 0;
        }

        .progress-bar {
            width: 100%;
            height: 24px;
            background: #e2e8f0;
            border-radius: var(--radius-md);
            overflow: hidden;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: var(--color-primary);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .progress-text {
            text-align: center;
            margin-top: var(--space-sm);
            color: var(--color-text-light);
            font-size: 0.875rem;
        }

        /* ============================================
           IMAGE PREVIEW MODAL
           ============================================ */
        .image-preview-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }

        .image-preview-modal.active {
            display: flex;
        }

        .image-preview-modal img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
        }

        .modal-close-btn {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            color: white;
            cursor: pointer;
            background: none;
            border: none;
            width: auto;
            height: auto;
            padding: 0;
        }

        /* ============================================
           LOADING & MESSAGES
           ============================================ */
        .loading {
            text-align: center;
            padding: var(--space-2xl);
        }

        .spinner {
            border: 4px solid #e2e8f0;
            border-top: 4px solid var(--color-primary);
            border-radius: 50%;
            width: 48px;
            height: 48px;
            animation: spin 1s linear infinite;
            margin: 0 auto var(--space-lg);
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .message {
            padding: var(--space-lg);
            border-radius: var(--radius-md);
            margin: var(--space-lg) 0;
        }

        .message-success {
            background: #d1fae5;
            color: #065f46;
            border: 2px solid var(--color-success);
        }

        .message-error {
            background: #fef2f2;
            color: #991b1b;
            border: 2px solid var(--color-danger);
        }

        .message-info {
            background: #dbeafe;
            color: #1e40af;
            border: 2px solid var(--color-primary);
        }

        /* ============================================
           RESPONSIVE
           ============================================ */
        @media (max-width: 768px) {
            .container {
                padding: var(--space-md);
            }

            .mode-grid {
                grid-template-columns: 1fr;
            }

            .image-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }

            .sticky-footer {
                flex-direction: column;
                gap: var(--space-md);
            }

            .footer-actions {
                width: 100%;
            }

            .footer-actions button {
                flex: 1;
            }

            .modal-content {
                padding: var(--space-lg);
            }

            .btn-group {
                flex-direction: column;
            }

            .btn-group button {
                width: 100%;
            }
        }

        /* ============================================
           UTILITY CLASSES
           ============================================ */
        .hidden {
            display: none !important;
        }

        .text-center {
            text-align: center;
        }

        .mb-lg {
            margin-bottom: var(--space-lg);
        }

        .mt-lg {
            margin-top: var(--space-lg);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- ============================================
             MODE SELECTION SCREEN
             ============================================ -->
        <div id="modeSelection" class="screen active">
            <div class="app-header">
                <h1>🌿 Plant Image Duplicate Finder</h1>
                <p>Find and remove duplicate and similar images</p>
            </div>

            <h2 class="text-center mb-lg">What would you like to find?</h2>

            <div class="mode-grid">
                <div class="mode-card" data-mode="duplicates">
                    <div class="mode-card-icon">🔍</div>
                    <h3>Exact Duplicates</h3>
                    <p>Same image, different copy</p>
                    <small>Uses perceptual hashing</small>
                </div>

                <div class="mode-card" data-mode="similar">
                    <div class="mode-card-icon">🎨</div>
                    <h3>Similar Images</h3>
                    <p>Different shots, same plant</p>
                    <small>Uses AI to detect visual similarity</small>
                </div>

                <div class="mode-card" data-mode="outliers">
                    <div class="mode-card-icon">⚠️</div>
                    <h3>Outliers</h3>
                    <p>Images that don't belong</p>
                    <small>Find images in wrong folder</small>
                </div>
            </div>

            <div class="scope-selector">
                <h3>Scan Options</h3>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="scopeAll" name="scope" value="all" checked>
                        <label for="scopeAll">
                            <strong>All Species (Recommended)</strong><br>
                            <small>Scan all species folders at once</small>
                        </label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="scopeSingle" name="scope" value="single">
                        <label for="scopeSingle">
                            <strong>Single Species</strong><br>
                            <small>Scan only one species folder</small>
                        </label>
                    </div>
                </div>

                <div class="species-dropdown hidden" id="speciesDropdownContainer">
                    <select id="speciesSelect" disabled>
                        <option value="">Loading species...</option>
                    </select>
                </div>
            </div>

            <div class="btn-group">
                <button class="btn btn-primary btn-block" id="startAnalysisBtn">
                    Start Analysis
                </button>
            </div>
        </div>

        <!-- ============================================
             RESULTS VIEW
             ============================================ -->
        <div id="resultsView" class="screen">
            <div class="results-header">
                <h2 id="resultsTitle">Analysis Results</h2>
                <div class="results-stats" id="resultsStats"></div>
                <div class="results-actions">
                    <button class="btn btn-secondary" id="backToModeBtn">
                        ← Back to Mode Selection
                    </button>
                </div>
            </div>

            <div id="resultsContent"></div>

            <div class="sticky-footer" id="stickyFooter">
                <div class="selection-count">
                    <span id="selectionCount">0</span> images selected for deletion
                </div>
                <div class="footer-actions">
                    <button class="btn btn-secondary" id="clearSelectionBtn">
                        Clear Selection
                    </button>
                    <button class="btn btn-danger" id="deleteSelectedBtn" disabled>
                        Delete Selected
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- ============================================
         DELETION CONFIRMATION MODAL
         ============================================ -->
    <div class="modal" id="confirmModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-icon">⚠️</div>
                <h2>Confirm Deletion</h2>
            </div>
            <div class="modal-body">
                <p>You're about to permanently delete:</p>

                <div class="deletion-summary">
                    <div class="deletion-summary-stat" id="deleteCount">0</div>
                    <div class="deletion-summary-label">images</div>
                    <div class="deletion-summary-label mt-lg" id="deleteSummary"></div>
                </div>

                <div class="warning-message">
                    <strong>⚠️ This cannot be undone!</strong>
                </div>

                <details>
                    <summary style="cursor: pointer; padding: var(--space-sm); font-weight: 600;">
                        View list of files to delete
                    </summary>
                    <div class="file-list" id="fileList"></div>
                </details>
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" id="cancelDeleteBtn">
                    Cancel
                </button>
                <button class="btn btn-danger" id="confirmDeleteBtn">
                    Yes, Delete Files
                </button>
            </div>
        </div>
    </div>

    <!-- ============================================
         PROGRESS MODAL
         ============================================ -->
    <div class="modal" id="progressModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-icon">🗑️</div>
                <h2 id="progressTitle">Deleting Files...</h2>
            </div>
            <div class="modal-body">
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%">
                            0%
                        </div>
                    </div>
                    <div class="progress-text" id="progressText">
                        Preparing deletion...
                    </div>
                </div>
                <div id="progressDetails" class="mt-lg"></div>
            </div>
        </div>
    </div>

    <!-- ============================================
         IMAGE PREVIEW MODAL
         ============================================ -->
    <div class="image-preview-modal" id="imagePreviewModal">
        <button class="modal-close-btn" onclick="closeImagePreview()">&times;</button>
        <img id="previewImage" src="" alt="Full size preview">
    </div>

    <!-- ============================================
         JAVASCRIPT
         ============================================ -->
    <script>
        /* ============================================
           STATE MANAGEMENT
           ============================================ */
        const AppState = {
            currentMode: null,
            currentScope: 'all',
            currentSpecies: null,
            resultsData: null,
            selectedImages: new Set(),

            selectImage(path) {
                this.selectedImages.add(path);
                updateSelectionCounter();
            },

            deselectImage(path) {
                this.selectedImages.delete(path);
                updateSelectionCounter();
            },

            clearSelection() {
                this.selectedImages.clear();
                updateSelectionCounter();
                // Remove visual indicators
                document.querySelectorAll('.image-item.selected').forEach(item => {
                    item.classList.remove('selected');
                });
            },

            getSelectedCount() {
                return this.selectedImages.size;
            },

            reset() {
                this.currentMode = null;
                this.currentScope = 'all';
                this.currentSpecies = null;
                this.resultsData = null;
                this.clearSelection();
            }
        };

        /* ============================================
           INITIALIZATION
           ============================================ */
        document.addEventListener('DOMContentLoaded', () => {
            loadSpeciesList();
            setupEventListeners();
        });

        function setupEventListeners() {
            // Mode cards
            document.querySelectorAll('.mode-card').forEach(card => {
                card.addEventListener('click', () => {
                    document.querySelectorAll('.mode-card').forEach(c => c.style.borderColor = 'var(--color-border)');
                    card.style.borderColor = 'var(--color-primary)';
                    AppState.currentMode = card.dataset.mode;
                });
            });

            // Scope selection
            document.querySelectorAll('input[name="scope"]').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    AppState.currentScope = e.target.value;
                    const dropdown = document.getElementById('speciesDropdownContainer');
                    const select = document.getElementById('speciesSelect');

                    if (e.target.value === 'single') {
                        dropdown.classList.remove('hidden');
                        select.disabled = false;
                    } else {
                        dropdown.classList.add('hidden');
                        select.disabled = true;
                    }
                });
            });

            // Species selection
            document.getElementById('speciesSelect').addEventListener('change', (e) => {
                AppState.currentSpecies = e.target.value;
            });

            // Start analysis button
            document.getElementById('startAnalysisBtn').addEventListener('click', startAnalysis);

            // Back to mode selection
            document.getElementById('backToModeBtn').addEventListener('click', () => {
                showScreen('modeSelection');
                AppState.reset();
            });

            // Clear selection
            document.getElementById('clearSelectionBtn').addEventListener('click', () => {
                AppState.clearSelection();
            });

            // Delete selected
            document.getElementById('deleteSelectedBtn').addEventListener('click', showDeleteConfirmation);

            // Modal actions
            document.getElementById('cancelDeleteBtn').addEventListener('click', () => {
                hideModal('confirmModal');
            });

            document.getElementById('confirmDeleteBtn').addEventListener('click', executeDelete);

            // Image preview modal
            document.getElementById('imagePreviewModal').addEventListener('click', closeImagePreview);
        }

        /* ============================================
           API CALLS
           ============================================ */
        async function loadSpeciesList() {
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
                showError('Failed to load species list');
            }
        }

        async function startAnalysis() {
            if (!AppState.currentMode) {
                alert('Please select a detection mode');
                return;
            }

            if (AppState.currentScope === 'single' && !AppState.currentSpecies) {
                alert('Please select a species');
                return;
            }

            showScreen('resultsView');
            showLoading('Analyzing images...');

            try {
                let data;
                const scope = AppState.currentScope === 'all' ? 'all' : AppState.currentSpecies;

                if (AppState.currentMode === 'duplicates') {
                    data = await analyzeForDuplicates(scope);
                } else if (AppState.currentMode === 'similar') {
                    data = await analyzeForSimilar(scope);
                } else if (AppState.currentMode === 'outliers') {
                    data = await analyzeForOutliers(scope);
                }

                // Validate data was received
                if (!data) {
                    throw new Error('No data received from server');
                }

                // Log response for debugging
                console.log('Analysis completed, received data:', {
                    mode: AppState.currentMode,
                    keys: Object.keys(data),
                    hasGroups: !!(data.similar_groups || data.duplicate_groups || data.species_results)
                });

                AppState.resultsData = data;
                displayResults(data);
            } catch (error) {
                console.error('Analysis failed:', error);
                showError('Analysis failed: ' + error.message);
            }
        }

        async function analyzeForDuplicates(scope) {
            const url = scope === 'all'
                ? '/api/duplicates/all?hash_size=16&threshold=5'
                : `/api/duplicates/${scope}?hash_size=16&threshold=5`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to analyze duplicates');
            return await response.json();
        }

        async function analyzeForSimilar(scope) {
            const url = scope === 'all'
                ? '/api/similarity/all?threshold=0.85'
                : `/api/similarity/${scope}?threshold=0.85`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to analyze similarity');
            return await response.json();
        }

        async function analyzeForOutliers(scope) {
            // Outliers use CNN similarity with low threshold
            const url = scope === 'all'
                ? '/api/similarity/all?threshold=0.5'
                : `/api/similarity/${scope}?threshold=0.5`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to analyze outliers');
            return await response.json();
        }

        async function executeDelete() {
            const files = Array.from(AppState.selectedImages);

            hideModal('confirmModal');
            showModal('progressModal');

            try {
                // Simulate progress (replace with actual progress tracking if backend supports it)
                updateProgress(0, files.length, 'Starting deletion...');

                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files })
                });

                if (!response.ok) throw new Error('Deletion failed');

                const result = await response.json();

                updateProgress(files.length, files.length, 'Complete!');

                setTimeout(() => {
                    hideModal('progressModal');
                    showDeletionComplete(result);

                    // Refresh the current view
                    startAnalysis();
                }, 1000);

            } catch (error) {
                hideModal('progressModal');
                showError('Deletion failed: ' + error.message);
            }
        }

        /* ============================================
           UI RENDERING
           ============================================ */
        function displayResults(data) {
            const content = document.getElementById('resultsContent');
            const statsDiv = document.getElementById('resultsStats');
            const titleDiv = document.getElementById('resultsTitle');

            // Handle backend errors
            if (data.error) {
                showError(data.error);
                return;
            }

            // Defensive check for unexpected data format
            if (!data.similar_groups && !data.duplicate_groups && !data.species_results && !data.mode) {
                console.error('Unexpected data format received:', data);
                showError('Received unexpected data format from server. Check console for details.');
                return;
            }

            // Handle different result formats
            if (data.mode === 'all_species_cnn' || data.species_results) {
                // All species CNN similarity results
                titleDiv.textContent = `Found ${data.total_groups || 0} groups across ${data.species_with_similarities || 0} species`;
                statsDiv.textContent = `${data.total_images || 0} images scanned`;

                const species_results = data.species_results || [];
                if (species_results.length === 0) {
                    content.innerHTML = '<div class="message message-info">No similar images found</div>';
                    return;
                }

                content.innerHTML = species_results.map(speciesData =>
                    renderSpeciesSection(speciesData)
                ).join('');

            } else if (data.similar_groups) {
                // Single species CNN similarity
                const groupCount = data.similar_groups.length;
                titleDiv.textContent = `Found ${groupCount} similar group${groupCount !== 1 ? 's' : ''}`;
                statsDiv.textContent = `${data.total_images || 0} images analyzed`;

                if (groupCount === 0) {
                    content.innerHTML = '<div class="message message-info">No similar images found</div>';
                    return;
                }

                content.innerHTML = renderSpeciesSection(data);

            } else if (data.duplicate_groups) {
                // Duplicate results
                const groupCount = data.duplicate_groups.length;
                titleDiv.textContent = `Found ${groupCount} duplicate group${groupCount !== 1 ? 's' : ''}`;
                statsDiv.textContent = `${data.total_images || 0} images scanned`;

                if (groupCount === 0) {
                    content.innerHTML = '<div class="message message-info">No duplicates found</div>';
                    return;
                }

                content.innerHTML = renderDuplicateGroups(data);
            } else {
                content.innerHTML = '<div class="message message-error">Unknown data format</div>';
            }

            // Setup group toggle handlers
            setupGroupToggles();
            setupImageSelectionHandlers();
        }

        function renderSpeciesSection(speciesData) {
            const speciesName = speciesData.species_name || speciesData.species || 'Unknown';
            const groups = speciesData.similar_groups || [];

            if (groups.length === 0) return '';

            return `
                <div class="species-section">
                    <div class="species-header">
                        <h3>${speciesName.replace(/_/g, ' ')}</h3>
                        <p>${groups.length} group${groups.length !== 1 ? 's' : ''} found</p>
                    </div>
                    ${groups.map((group, idx) => renderImageGroup(group, speciesName, idx)).join('')}
                </div>
            `;
        }

        function renderImageGroup(group, speciesName, groupIndex) {
            const groupId = `group-${speciesName}-${groupIndex}`;
            const images = group.images || [];

            // Sort images by size to identify largest
            const sortedImages = [...images].sort((a, b) => (b.size || 0) - (a.size || 0));
            const largestSize = sortedImages[0]?.size || 0;

            return `
                <div class="image-group" data-group-id="${groupId}">
                    <div class="group-header" onclick="toggleGroup('${groupId}')">
                        <div class="group-title">
                            Group ${group.group_id || groupIndex + 1}: ${images.length} images
                        </div>
                        <div class="group-actions">
                            <button class="btn btn-secondary" onclick="selectAllButLargest(event, '${groupId}', '${speciesName}')">
                                Select All But Largest
                            </button>
                            <span>▼</span>
                        </div>
                    </div>
                    <div class="group-content" id="${groupId}">
                        <div class="image-grid">
                            ${images.map(img => renderImageItem(img, speciesName, img.size === largestSize)).join('')}
                        </div>
                    </div>
                </div>
            `;
        }

        function renderDuplicateGroups(data) {
            // For duplicates, we want to render all groups
            const groups = data.duplicate_groups || [];

            return groups.map((group, idx) => {
                const groupId = `dup-group-${idx}`;
                const speciesName = data.species_name || data.species || 'Unknown';

                // Combine keep and duplicates
                const allImages = [group.keep, ...group.duplicates];
                const largestSize = group.keep.size || 0;

                return `
                    <div class="image-group" data-group-id="${groupId}">
                        <div class="group-header" onclick="toggleGroup('${groupId}')">
                            <div class="group-title">
                                Group ${idx + 1}: ${allImages.length} images (${group.duplicates.length} duplicate${group.duplicates.length !== 1 ? 's' : ''})
                            </div>
                            <div class="group-actions">
                                <button class="btn btn-secondary" onclick="selectDuplicates(event, '${groupId}', '${speciesName}')">
                                    Select Duplicates
                                </button>
                                <span>▼</span>
                            </div>
                        </div>
                        <div class="group-content" id="${groupId}">
                            <div class="image-grid">
                                ${renderImageItem(group.keep, speciesName, true)}
                                ${group.duplicates.map(img => renderImageItem(img, speciesName, false)).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function renderImageItem(image, speciesName, isLargest) {
            const imagePath = `${speciesName}/${image.filename}`;
            const imageUrl = image.path || `/images/${imagePath}`;
            const sizeKB = image.size ? Math.round(image.size / 1024) : 0;

            return `
                <div class="image-item ${isLargest ? 'keep' : ''}"
                     data-image-path="${imagePath}"
                     onclick="toggleImageSelection('${imagePath}')">
                    <div class="image-checkbox"></div>
                    <div class="image-wrapper">
                        <img src="${imageUrl}" alt="${image.filename}" loading="lazy"
                             onclick="event.stopPropagation(); showImagePreview('${imageUrl}')">
                    </div>
                    <div class="image-info">
                        <div class="image-filename" title="${image.filename}">${image.filename}</div>
                        <div class="image-meta">
                            <span>${sizeKB} KB</span>
                            ${isLargest ? '<span class="size-badge largest">🟢 Largest</span>' : '<span class="size-badge smaller">🟡 Smaller</span>'}
                        </div>
                    </div>
                </div>
            `;
        }

        /* ============================================
           IMAGE SELECTION
           ============================================ */
        function setupImageSelectionHandlers() {
            // Handlers are set via onclick in HTML
        }

        function toggleImageSelection(imagePath) {
            const imageItem = document.querySelector(`[data-image-path="${imagePath}"]`);
            if (!imageItem) return;

            if (AppState.selectedImages.has(imagePath)) {
                AppState.deselectImage(imagePath);
                imageItem.classList.remove('selected');
                imageItem.querySelector('.image-checkbox').textContent = '';
            } else {
                AppState.selectImage(imagePath);
                imageItem.classList.add('selected');
                imageItem.querySelector('.image-checkbox').textContent = '✓';
            }
        }

        function selectAllButLargest(event, groupId, speciesName) {
            event.stopPropagation();

            const group = document.querySelector(`[data-group-id="${groupId}"]`);
            const images = group.querySelectorAll('.image-item:not(.keep)');

            images.forEach(img => {
                const path = img.dataset.imagePath;
                if (!AppState.selectedImages.has(path)) {
                    AppState.selectImage(path);
                    img.classList.add('selected');
                    img.querySelector('.image-checkbox').textContent = '✓';
                }
            });
        }

        function selectDuplicates(event, groupId, speciesName) {
            event.stopPropagation();

            const group = document.querySelector(`[data-group-id="${groupId}"]`);
            const images = group.querySelectorAll('.image-item:not(.keep)');

            images.forEach(img => {
                const path = img.dataset.imagePath;
                if (!AppState.selectedImages.has(path)) {
                    AppState.selectImage(path);
                    img.classList.add('selected');
                    img.querySelector('.image-checkbox').textContent = '✓';
                }
            });
        }

        function updateSelectionCounter() {
            const count = AppState.getSelectedCount();
            document.getElementById('selectionCount').textContent = count;
            document.getElementById('deleteSelectedBtn').disabled = count === 0;
        }

        /* ============================================
           GROUP COLLAPSING
           ============================================ */
        function setupGroupToggles() {
            // Handlers are set via onclick in HTML
        }

        function toggleGroup(groupId) {
            const content = document.getElementById(groupId);
            if (content) {
                content.classList.toggle('expanded');
            }
        }

        /* ============================================
           DELETION WORKFLOW
           ============================================ */
        function showDeleteConfirmation() {
            const count = AppState.getSelectedCount();
            if (count === 0) return;

            const files = Array.from(AppState.selectedImages);

            // Calculate total size
            let totalSize = 0;
            const speciesCount = new Set();

            files.forEach(path => {
                const [species] = path.split('/');
                speciesCount.add(species);

                // Try to find the image element to get size
                const imgEl = document.querySelector(`[data-image-path="${path}"]`);
                if (imgEl) {
                    const sizeText = imgEl.querySelector('.image-meta span')?.textContent;
                    if (sizeText) {
                        const kb = parseInt(sizeText);
                        totalSize += kb;
                    }
                }
            });

            document.getElementById('deleteCount').textContent = count;
            document.getElementById('deleteSummary').innerHTML = `
                across ${speciesCount.size} species<br>
                Total size: ${(totalSize / 1024).toFixed(1)} MB
            `;

            const fileList = document.getElementById('fileList');
            fileList.innerHTML = files.map(f =>
                `<div class="file-list-item">${f}</div>`
            ).join('');

            showModal('confirmModal');
        }

        function showDeletionComplete(result) {
            const content = document.getElementById('resultsContent');
            const message = `
                <div class="message message-success">
                    <h3>✅ Deletion Complete</h3>
                    <p style="margin-top: var(--space-md);">
                        Successfully deleted: <strong>${result.deleted_count || 0}</strong> files<br>
                        ${result.error_count ? `Failed: <strong>${result.error_count}</strong><br>` : ''}
                    </p>
                </div>
            `;

            content.insertAdjacentHTML('afterbegin', message);

            AppState.clearSelection();
        }

        /* ============================================
           MODALS
           ============================================ */
        function showModal(modalId) {
            document.getElementById(modalId).classList.add('active');
        }

        function hideModal(modalId) {
            document.getElementById(modalId).classList.remove('active');
        }

        function showImagePreview(src) {
            document.getElementById('previewImage').src = src;
            document.getElementById('imagePreviewModal').classList.add('active');
        }

        function closeImagePreview() {
            document.getElementById('imagePreviewModal').classList.remove('active');
        }

        /* ============================================
           SCREEN MANAGEMENT
           ============================================ */
        function showScreen(screenId) {
            document.querySelectorAll('.screen').forEach(screen => {
                screen.classList.remove('active');
            });
            document.getElementById(screenId).classList.add('active');
        }

        /* ============================================
           LOADING & MESSAGES
           ============================================ */
        function showLoading(message) {
            const content = document.getElementById('resultsContent');
            content.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>${message}</p>
                </div>
            `;
        }

        function showError(message) {
            const content = document.getElementById('resultsContent');
            content.innerHTML = `
                <div class="message message-error">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }

        function updateProgress(current, total, message) {
            const percent = Math.round((current / total) * 100);
            document.getElementById('progressFill').style.width = `${percent}%`;
            document.getElementById('progressFill').textContent = `${percent}%`;
            document.getElementById('progressText').textContent = message || `${current} of ${total} files`;
        }

        /* ============================================
           KEYBOARD SHORTCUTS
           ============================================ */
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeImagePreview();

                // Close any open modals
                document.querySelectorAll('.modal.active').forEach(modal => {
                    modal.classList.remove('active');
                });
            }
        });
    </script>
</body>
</html>
"""
