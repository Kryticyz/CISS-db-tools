"""
HTTP request handlers for the duplicate review server.
"""

import http.server
import json
import mimetypes
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from .html_template import generate_html_page


class DuplicateReviewHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the duplicate review server."""

    # Class variables that will be set by the server
    base_dir: Optional[Path] = None
    detection_api: Optional[Any] = None
    faiss_store: Optional[Any] = None

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

        # Main page
        if path == "/" or path == "/index.html":
            self.send_html(generate_html_page())
            return

        # API: Get species list
        if path == "/api/species":
            if self.detection_api and self.base_dir:
                from ..core.detection import get_species_list

                species = get_species_list(self.base_dir)
                self.send_json(species)
            else:
                self.send_json({"error": "Server not properly configured"}, 500)
            return

        # API: CNN availability check
        if path == "/api/cnn/status":
            from ..core.detection import CNN_AVAILABLE, DEFAULT_MODEL

            self.send_json({"available": CNN_AVAILABLE, "model": DEFAULT_MODEL})
            return

        # API: FAISS status check
        if path == "/api/faiss/status":
            if self.faiss_store:
                status = self.faiss_store.get_status()
                self.send_json(status)
            else:
                self.send_json({"available": False, "count": 0, "location": None})
            return

        # API: Get CNN similarity for species
        if path.startswith("/api/similarity/"):
            species_name = urllib.parse.unquote(path[16:])
            threshold = float(query.get("threshold", ["0.85"])[0])
            model = query.get("model", ["resnet18"])[0]

            if self.detection_api and self.base_dir:
                result = self.detection_api.get_species_cnn_similarity(
                    self.base_dir, species_name, threshold, model
                )
                self.send_json(result)
            else:
                self.send_json({"error": "Server not properly configured"}, 500)
            return

        # API: Get all species duplicates
        if path == "/api/duplicates/all":
            hash_size = int(query.get("hash_size", ["16"])[0])
            threshold = int(query.get("threshold", ["5"])[0])

            if self.detection_api and self.base_dir:
                result = self.detection_api.get_all_species_duplicates(
                    self.base_dir, hash_size, threshold
                )
                self.send_json(result)
            else:
                self.send_json({"error": "Server not properly configured"}, 500)
            return

        # API: Get CNN similarity for all species
        if path == "/api/similarity/all":
            threshold = float(query.get("threshold", ["0.85"])[0])
            model = query.get("model", ["resnet18"])[0]

            if self.detection_api and self.base_dir:
                result = self.detection_api.get_all_species_cnn_similarity(
                    self.base_dir, threshold, model
                )
                self.send_json(result)
            else:
                self.send_json({"error": "Server not properly configured"}, 500)
            return

        # API: Get species duplicates
        if path.startswith("/api/duplicates/"):
            species_name = urllib.parse.unquote(path[16:])
            hash_size = int(query.get("hash_size", ["16"])[0])
            threshold = int(query.get("threshold", ["5"])[0])

            if self.detection_api and self.base_dir:
                result = self.detection_api.get_species_duplicates(
                    self.base_dir, species_name, hash_size, threshold
                )
                self.send_json(result)
            else:
                self.send_json({"error": "Server not properly configured"}, 500)
            return

        # Serve images
        if path.startswith("/image/"):
            parts = path[7:].split("/", 1)
            if len(parts) == 2 and self.base_dir:
                species_name = urllib.parse.unquote(parts[0])
                filename = urllib.parse.unquote(parts[1])
                image_path = (self.base_dir / species_name / filename).resolve()
                if image_path.is_relative_to(self.base_dir.resolve()):
                    self.send_image(image_path)
                    return
            self.send_error(404, "Image not found")
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API: Delete files
        if path == "/api/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                files = data.get("files", [])

                if self.detection_api and self.base_dir:
                    result = self.detection_api.delete_files(self.base_dir, files)
                    self.send_json(result)
                else:
                    self.send_json(
                        {"success": False, "error": "Server not properly configured"},
                        500,
                    )
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)
            return

        self.send_error(404, "Not found")


def create_handler_class(
    base_dir: Path, detection_api: Any, faiss_store: Optional[Any]
):
    """
    Create a handler class with injected dependencies.

    Args:
        base_dir: Base directory containing species subdirectories
        detection_api: Detection API instance with caches
        faiss_store: Optional FAISS store instance

    Returns:
        Handler class configured with dependencies
    """

    class ConfiguredHandler(DuplicateReviewHandler):
        pass

    ConfiguredHandler.base_dir = base_dir
    ConfiguredHandler.detection_api = detection_api
    ConfiguredHandler.faiss_store = faiss_store

    return ConfiguredHandler
