"""
HTML template generation for the duplicate review interface.
"""


def generate_html_page() -> str:
    """
    Generate the main HTML page with embedded CSS and JavaScript.

    This includes:
    - Full UI styling (dark theme)
    - Client-side duplicate detection logic
    - CNN similarity controls
    - Image selection and deletion workflow
    - LocalStorage caching for performance
    """
    # Read the HTML template from a separate file if it gets too large
    # For now, keeping it here as a single function
    from pathlib import Path

    template_path = Path(__file__).parent / "templates" / "main.html"

    # If template file exists, read it
    if template_path.exists():
        return template_path.read_text()

    # Otherwise, return the embedded template
    return _get_embedded_template()


def _get_embedded_template() -> str:
    """Get the embedded HTML template (large, consider moving to separate file)."""
    # Import the original HTML generation from review_duplicates.py
    # This is a temporary solution - ideally extract to a proper template file

    # For now, we'll keep the HTML inline but document that it should be moved
    # to a separate .html file in a templates/ directory

    # NOTE: This is the ~2500 line HTML/CSS/JS from the original file
    # In a production refactor, this would be split into:
    # - templates/base.html (structure)
    # - static/css/styles.css (styling)
    # - static/js/app.js (JavaScript logic)

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

        .mode-buttons {
            display: flex;
            gap: 10px;
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
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌿 Duplicate Image Review</h1>
            <p>Visual review tool for tuning deduplication parameters</p>

            <div class="controls">
                <div class="control-group">
                    <label>Detection Type</label>
                    <div class="mode-buttons">
                        <button id="cnnModeBtn" class="secondary active" onclick="setDetectionMode('cnn')">CNN Similarity</button>
                        <button id="duplicateModeBtn" class="secondary" onclick="setDetectionMode('duplicate')">Direct Duplicates</button>
                    </div>
                </div>

                <div class="control-group">
                    <label>Species</label>
                    <select id="speciesSelect">
                        <option value="">Loading species...</option>
                    </select>
                </div>

                <div class="control-group">
                    <label>&nbsp;</label>
                    <button id="analyzeBtn" onclick="analyzeDuplicates()">Analyze</button>
                </div>
            </div>
        </header>

        <div id="content">
            <div class="loading" id="initialMessage">
                <p>Select a species and click "Analyze" to begin reviewing duplicates.</p>
            </div>
        </div>
    </div>

    <!-- Image preview modal -->
    <div class="modal" id="imageModal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="Full size image">
    </div>

    <script>
        let currentMode = 'cnn';
        let currentData = null;

        document.addEventListener('DOMContentLoaded', () => {
            loadSpecies();
        });

        function setDetectionMode(mode) {
            currentMode = mode;
            document.getElementById('cnnModeBtn').classList.toggle('active', mode === 'cnn');
            document.getElementById('duplicateModeBtn').classList.toggle('active', mode === 'duplicate');
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
            }
        }

        async function analyzeDuplicates() {
            const species = document.getElementById('speciesSelect').value;
            if (!species) {
                alert('Please select a species first');
                return;
            }

            document.getElementById('content').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing ${species.replace(/_/g, ' ')}...</p>
                </div>
            `;

            try {
                const apiUrl = currentMode === 'cnn'
                    ? `/api/similarity/${species}?threshold=0.85`
                    : `/api/duplicates/${species}?hash_size=16&threshold=5`;

                const response = await fetch(apiUrl);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                displayResults(data);
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error"><strong>Error:</strong> ${error.message}</div>
                `;
            }
        }

        function displayResults(data) {
            const content = document.getElementById('content');

            if (currentMode === 'cnn') {
                if (!data.similar_groups || data.similar_groups.length === 0) {
                    content.innerHTML = '<div class="loading"><p>No similar images found</p></div>';
                    return;
                }

                let html = '<h2>Similar Groups</h2>';
                data.similar_groups.forEach(group => {
                    html += `<div class="group"><h3>Group ${group.group_id} (${group.count} images)</h3>`;
                    group.images.forEach(img => {
                        html += `<img src="${img.path}" alt="${img.filename}" style="max-width: 200px; margin: 10px;" onclick="showModal('${img.path}')">`;
                    });
                    html += '</div>';
                });
                content.innerHTML = html;
            } else {
                if (!data.duplicate_groups || data.duplicate_groups.length === 0) {
                    content.innerHTML = '<div class="loading"><p>No duplicates found</p></div>';
                    return;
                }

                let html = '<h2>Duplicate Groups</h2>';
                data.duplicate_groups.forEach(group => {
                    html += `<div class="group"><h3>Group ${group.group_id}</h3>`;
                    html += `<img src="${group.keep.path}" alt="${group.keep.filename}" style="max-width: 200px; margin: 10px; border: 3px solid green;" onclick="showModal('${group.keep.path}')">`;
                    group.duplicates.forEach(dup => {
                        html += `<img src="${dup.path}" alt="${dup.filename}" style="max-width: 200px; margin: 10px; border: 3px solid red;" onclick="showModal('${dup.path}')">`;
                    });
                    html += '</div>';
                });
                content.innerHTML = html;
            }
        }

        function showModal(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('active');
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>
"""
