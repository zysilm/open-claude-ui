"""
E2E Integration tests for settings and API key management.
Tests the complete flow of API key configuration and validation.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient


@pytest.mark.integration
class TestApiKeyListFlow:
    """Test API key listing operations."""

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, client: AsyncClient):
        """Test listing API keys when none are configured."""
        response = await client.get("/api/v1/settings/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert "api_keys" in data
        assert data["api_keys"] == []

    @pytest.mark.asyncio
    async def test_list_api_keys_after_creation(self, client: AsyncClient):
        """Test listing API keys after creating some."""
        # Create API key
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"encrypted_test_key"

            await client.post(
                "/api/v1/settings/api-keys", json={"provider": "openai", "api_key": "sk-test123"}
            )

        # List keys
        response = await client.get("/api/v1/settings/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) >= 1

        # Find the openai key
        openai_keys = [k for k in data["api_keys"] if k["provider"] == "openai"]
        assert len(openai_keys) == 1
        assert openai_keys[0]["is_configured"] is True
        # Should not expose actual key
        assert "encrypted_key" not in openai_keys[0]
        assert "api_key" not in openai_keys[0]


@pytest.mark.integration
class TestApiKeySetFlow:
    """Test API key creation and update operations."""

    @pytest.mark.asyncio
    async def test_set_new_api_key(self, client: AsyncClient):
        """Test setting a new API key."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"encrypted_anthropic_key"

            response = await client.post(
                "/api/v1/settings/api-keys",
                json={"provider": "anthropic", "api_key": "sk-ant-test123"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "anthropic" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_update_existing_api_key(self, client: AsyncClient):
        """Test updating an existing API key."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            # First creation
            mock_enc.return_value.encrypt.return_value = b"old_encrypted_key"
            await client.post(
                "/api/v1/settings/api-keys", json={"provider": "azure", "api_key": "old-key"}
            )

            # Update
            mock_enc.return_value.encrypt.return_value = b"new_encrypted_key"
            response = await client.post(
                "/api/v1/settings/api-keys", json={"provider": "azure", "api_key": "new-key"}
            )

            assert response.status_code == 201
            # Key should be updated successfully

    @pytest.mark.asyncio
    async def test_set_multiple_providers(self, client: AsyncClient):
        """Test setting API keys for multiple providers."""
        providers = ["openai", "anthropic", "azure"]

        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            for provider in providers:
                mock_enc.return_value.encrypt.return_value = f"encrypted_{provider}".encode()

                response = await client.post(
                    "/api/v1/settings/api-keys",
                    json={"provider": provider, "api_key": f"sk-{provider}-test"},
                )
                assert response.status_code == 201

        # Verify all are listed
        list_response = await client.get("/api/v1/settings/api-keys")
        assert list_response.status_code == 200
        configured_providers = {k["provider"] for k in list_response.json()["api_keys"]}
        for provider in providers:
            assert provider in configured_providers

    @pytest.mark.asyncio
    async def test_set_api_key_encryption_error(self, client: AsyncClient):
        """Test handling encryption errors."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.side_effect = Exception("Encryption failed")

            response = await client.post(
                "/api/v1/settings/api-keys", json={"provider": "openai", "api_key": "sk-test"}
            )

            assert response.status_code == 400
            assert "encrypt" in response.json()["detail"].lower()


@pytest.mark.integration
class TestApiKeyDeleteFlow:
    """Test API key deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, client: AsyncClient):
        """Test deleting a non-existent API key."""
        response = await client.delete("/api/v1/settings/api-keys/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, client: AsyncClient):
        """Test successfully deleting an API key."""
        # First create a key
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"to_delete_key"

            await client.post(
                "/api/v1/settings/api-keys",
                json={"provider": "delete_test", "api_key": "sk-delete-me"},
            )

        # Delete the key
        response = await client.delete("/api/v1/settings/api-keys/delete_test")
        assert response.status_code == 204

        # Verify deletion
        list_response = await client.get("/api/v1/settings/api-keys")
        providers = [k["provider"] for k in list_response.json()["api_keys"]]
        assert "delete_test" not in providers


@pytest.mark.integration
class TestApiKeyTestFlow:
    """Test API key validation operations."""

    @pytest.mark.asyncio
    async def test_test_api_key_valid(self, client: AsyncClient):
        """Test validating a valid API key."""
        with patch("app.core.llm.provider.LLMProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate = AsyncMock(return_value="Hello!")
            mock_provider.return_value = mock_instance

            response = await client.post(
                "/api/v1/settings/api-keys/test",
                json={"provider": "openai", "api_key": "sk-valid-test-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_test_api_key_invalid(self, client: AsyncClient):
        """Test validating an invalid API key."""
        with patch("app.core.llm.provider.LLMProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate = AsyncMock(side_effect=Exception("Invalid API key"))
            mock_provider.return_value = mock_instance

            response = await client.post(
                "/api/v1/settings/api-keys/test",
                json={"provider": "openai", "api_key": "sk-invalid-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "failed" in data["message"].lower() or "error" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_multiple_providers(self, client: AsyncClient):
        """Test validating keys for multiple providers."""
        providers = ["openai", "anthropic", "azure"]

        for provider in providers:
            with patch("app.core.llm.provider.LLMProvider") as mock_provider:
                mock_instance = MagicMock()
                mock_instance.generate = AsyncMock(return_value="Test response")
                mock_provider.return_value = mock_instance

                response = await client.post(
                    "/api/v1/settings/api-keys/test",
                    json={"provider": provider, "api_key": f"sk-{provider}-test"},
                )

                assert response.status_code == 200
                assert response.json()["valid"] is True


@pytest.mark.integration
class TestApiKeyWorkflow:
    """Test complete API key management workflow."""

    @pytest.mark.asyncio
    async def test_full_api_key_workflow(self, client: AsyncClient):
        """Test complete workflow: create -> list -> test -> update -> delete."""
        provider = "workflow_test"

        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            # 1. Create API key
            mock_enc.return_value.encrypt.return_value = b"initial_key"
            create_resp = await client.post(
                "/api/v1/settings/api-keys", json={"provider": provider, "api_key": "sk-initial"}
            )
            assert create_resp.status_code == 201

        # 2. List and verify
        list_resp = await client.get("/api/v1/settings/api-keys")
        assert list_resp.status_code == 200
        providers = [k["provider"] for k in list_resp.json()["api_keys"]]
        assert provider in providers

        # 3. Test the key
        with patch("app.core.llm.provider.LLMProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate = AsyncMock(return_value="Test")
            mock_provider.return_value = mock_instance

            test_resp = await client.post(
                "/api/v1/settings/api-keys/test", json={"provider": provider, "api_key": "sk-test"}
            )
            assert test_resp.status_code == 200

        # 4. Update the key
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"updated_key"
            update_resp = await client.post(
                "/api/v1/settings/api-keys", json={"provider": provider, "api_key": "sk-updated"}
            )
            assert update_resp.status_code == 201

        # 5. Delete the key
        delete_resp = await client.delete(f"/api/v1/settings/api-keys/{provider}")
        assert delete_resp.status_code == 204

        # 6. Verify deletion
        final_list = await client.get("/api/v1/settings/api-keys")
        providers_after = [k["provider"] for k in final_list.json()["api_keys"]]
        assert provider not in providers_after


@pytest.mark.integration
class TestApiKeyProviderIsolation:
    """Test that API keys for different providers are isolated."""

    @pytest.mark.asyncio
    async def test_provider_isolation(self, client: AsyncClient):
        """Test that operations on one provider don't affect others."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            # Create keys for two providers
            mock_enc.return_value.encrypt.return_value = b"key1"
            await client.post(
                "/api/v1/settings/api-keys", json={"provider": "provider_a", "api_key": "sk-a"}
            )

            mock_enc.return_value.encrypt.return_value = b"key2"
            await client.post(
                "/api/v1/settings/api-keys", json={"provider": "provider_b", "api_key": "sk-b"}
            )

        # Delete only provider_a
        await client.delete("/api/v1/settings/api-keys/provider_a")

        # Verify provider_b still exists
        list_resp = await client.get("/api/v1/settings/api-keys")
        providers = [k["provider"] for k in list_resp.json()["api_keys"]]
        assert "provider_a" not in providers
        assert "provider_b" in providers
