"""
Tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client: TestClient):
        """Test health check returns OK."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""

    def test_dashboard_status(self, test_client: TestClient):
        """Test dashboard status endpoint."""
        response = test_client.get("/api/dashboard/status")
        assert response.status_code == 200

        data = response.json()
        assert "faiss_available" in data
        assert "species_count" in data
        assert data["species_count"] == 2  # Test_Species_A and Test_Species_B


class TestAnalysisEndpoints:
    """Tests for analysis endpoints."""

    def test_get_parameters(self, test_client: TestClient):
        """Test getting parameter descriptions."""
        response = test_client.get("/api/analysis/parameters")
        assert response.status_code == 200

        data = response.json()
        assert "parameters" in data
        assert "current" in data
        assert len(data["parameters"]) == 4  # hash_size, hamming, similarity, percentile

    def test_duplicates_invalid_species(self, test_client: TestClient):
        """Test duplicates endpoint with invalid species."""
        response = test_client.get("/api/analysis/duplicates/Invalid_Species")
        assert response.status_code == 404

    def test_duplicates_valid_species(self, test_client: TestClient):
        """Test duplicates endpoint with valid species."""
        response = test_client.get("/api/analysis/duplicates/Test_Species_A")
        assert response.status_code == 200

        data = response.json()
        assert data["species_name"] == "Test_Species_A"
        assert "duplicate_groups" in data
        assert "total_duplicates" in data


class TestImageEndpoints:
    """Tests for image serving endpoints."""

    def test_get_image_invalid_species(self, test_client: TestClient):
        """Test getting image from invalid species."""
        response = test_client.get("/api/images/Invalid_Species/image.jpg")
        assert response.status_code == 404

    def test_get_image_invalid_extension(self, test_client: TestClient):
        """Test getting file with invalid extension."""
        response = test_client.get("/api/images/Test_Species_A/file.txt")
        assert response.status_code == 400

    def test_get_image_valid(self, test_client: TestClient):
        """Test getting a valid image."""
        response = test_client.get("/api/images/Test_Species_A/image_0.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"


class TestDeletionEndpoints:
    """Tests for deletion queue endpoints."""

    def test_get_empty_queue(self, test_client: TestClient):
        """Test getting empty deletion queue."""
        response = test_client.get("/api/deletion/queue")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 0
        assert data["files"] == []

    def test_add_to_queue(self, test_client: TestClient):
        """Test adding files to deletion queue."""
        response = test_client.post(
            "/api/deletion/queue",
            json={
                "files": [
                    {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000}
                ],
                "reason": "duplicate",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["added"] == 1
        assert data["total"] == 1

    def test_remove_from_queue(self, test_client: TestClient):
        """Test removing file from deletion queue."""
        # First add a file
        test_client.post(
            "/api/deletion/queue",
            json={
                "files": [
                    {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000}
                ],
                "reason": "duplicate",
            },
        )

        # Then remove it
        response = test_client.delete(
            "/api/deletion/queue/Test_Species_A/image_0.jpg"
        )
        assert response.status_code == 200
        assert response.json()["removed"] is True

    def test_clear_queue(self, test_client: TestClient):
        """Test clearing deletion queue."""
        # Add some files
        test_client.post(
            "/api/deletion/queue",
            json={
                "files": [
                    {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000},
                    {"species": "Test_Species_A", "filename": "image_1.jpg", "size": 2000},
                ],
                "reason": "similar",
            },
        )

        # Clear
        response = test_client.post("/api/deletion/queue/clear")
        assert response.status_code == 200
        assert response.json()["cleared"] == 2

    def test_get_preview(self, test_client: TestClient):
        """Test getting deletion preview."""
        # Add some files
        test_client.post(
            "/api/deletion/queue",
            json={
                "files": [
                    {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000}
                ],
                "reason": "outlier",
            },
        )

        response = test_client.get("/api/deletion/preview")
        assert response.status_code == 200

        data = response.json()
        assert data["total_files"] == 1
        assert "outlier" in data["by_reason"]

    def test_confirm_deletion(self, test_client: TestClient):
        """Test confirming deletion."""
        # Add a file that exists
        test_client.post(
            "/api/deletion/queue",
            json={
                "files": [
                    {"species": "Test_Species_A", "filename": "image_0.jpg", "size": 1000}
                ],
                "reason": "duplicate",
            },
        )

        response = test_client.post("/api/deletion/confirm")
        assert response.status_code == 200

        data = response.json()
        assert data["deleted_count"] == 1
        assert data["success"] is True
