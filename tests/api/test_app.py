"""Tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from p1diff.api.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "P1 Diff API"
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "git_available" in data
    
    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["api_version"] == "v1"
        assert "supported_features" in data
    
    def test_diff_endpoint_validation(self, client):
        """Test diff endpoint input validation."""
        # Test missing required fields
        response = client.post("/diff", json={})
        assert response.status_code == 422
        
        # Test invalid repo URL
        response = client.post("/diff", json={
            "repo_url": "invalid-url",
            "commit_good": "abc123",
            "commit_candidate": "def456"
        })
        assert response.status_code == 422
        
        # Test invalid commit SHA (too short)
        response = client.post("/diff", json={
            "repo_url": "https://github.com/user/repo.git",
            "commit_good": "abc",
            "commit_candidate": "def456"
        })
        assert response.status_code == 422
        
        # Test cap_file > cap_total
        response = client.post("/diff", json={
            "repo_url": "https://github.com/user/repo.git",
            "commit_good": "abc123",
            "commit_candidate": "def456",
            "cap_total": 1000,
            "cap_file": 2000
        })
        assert response.status_code == 422
    
    def test_diff_endpoint_valid_request_structure(self, client):
        """Test that diff endpoint accepts valid request structure."""
        # This test validates the request structure without actually processing
        # (since we don't want to make real git calls in unit tests)
        
        valid_request = {
            "repo_url": "https://github.com/user/repo.git",
            "commit_good": "ba7765dd48c0ba51f4fd12cde48fd100aecdb743",
            "commit_candidate": "d7a39abec5a282b9955afdd1649a5f1bafae35f7",
            "branch_name": "feature/test",
            "cap_total": 800000,
            "cap_file": 64000,
            "context_lines": 3,
            "find_renames_threshold": 90
        }
        
        # This will fail at the git processing stage, but should pass validation
        response = client.post("/diff", json=valid_request)
        
        # We expect either success (if git repo is accessible) or a structured error
        assert response.status_code in [200, 500]
        data = response.json()
        
        # Should have the expected envelope structure
        assert "ok" in data
        
        if data["ok"]:
            # Success case - should have data structure like test_output.json
            assert "data" in data
            assert "provenance" in data["data"]
            assert "files" in data["data"]
        else:
            # Error case - should have error structure
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]
