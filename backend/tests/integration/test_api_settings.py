"""Integration tests for settings API endpoints."""

import pytest
from starlette.testclient import TestClient
from app.models.database import ApiKey
from sqlalchemy import select


class TestAPISettings:
    """Test class for Settings API endpoints."""

    def test_list_api_keys_empty(self, client: TestClient):
        """Test listing API keys when none are configured."""
        response = client.get("/api/v1/settings/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert "api_keys" in data
        assert data["api_keys"] == []

    def test_set_api_key(self, client: TestClient):
        """Test setting a new API key."""
        response = client.post(
            "/api/v1/settings/api-keys",
            json={"provider": "openai", "api_key": "sk-test123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "openai" in data["message"]

    def test_list_api_keys_with_data(self, client: TestClient):
        """Test listing API keys after adding one."""
        # Add a key first
        client.post(
            "/api/v1/settings/api-keys",
            json={"provider": "anthropic", "api_key": "sk-ant-test456"},
        )

        # List keys
        response = client.get("/api/v1/settings/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) == 1
        assert data["api_keys"][0]["provider"] == "anthropic"
        assert data["api_keys"][0]["is_configured"] is True
        # Verify the actual key is NOT returned
        assert "api_key" not in data["api_keys"][0]

    def test_update_existing_api_key(self, client: TestClient):
        """Test updating an existing API key."""
        # Add initial key
        client.post(
            "/api/v1/settings/api-keys",
            json={"provider": "openai", "api_key": "sk-old-key"},
        )

        # Update with new key
        response = client.post(
            "/api/v1/settings/api-keys",
            json={"provider": "openai", "api_key": "sk-new-key"},
        )
        assert response.status_code == 201

    def test_delete_api_key(self, client: TestClient):
        """Test deleting an API key."""
        # Add a key first
        client.post(
            "/api/v1/settings/api-keys",
            json={"provider": "azure", "api_key": "azure-test-key"},
        )

        # Delete it
        response = client.delete("/api/v1/settings/api-keys/azure")
        assert response.status_code == 204

    def test_delete_nonexistent_api_key(self, client: TestClient):
        """Test deleting an API key that doesn't exist."""
        response = client.delete("/api/v1/settings/api-keys/nonexistent")
        assert response.status_code == 404

    def test_test_api_key(self, client: TestClient):
        """Test the API key test endpoint."""
        # Note: This will fail unless you have a real API key
        # In a real test environment, you'd mock the LLM provider
        response = client.post(
            "/api/v1/settings/api-keys/test",
            json={"provider": "openai", "api_key": "invalid-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "message" in data
        # With an invalid key, it should return valid=False
        assert data["valid"] is False
