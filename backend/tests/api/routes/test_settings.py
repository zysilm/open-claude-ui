"""Tests for Settings API routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.api.routes.settings import router
from app.models.database import ApiKey


@pytest.fixture
def app(db_session):
    """Create FastAPI app with settings router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def get_test_db():
        yield db_session

    from app.core.storage.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.mark.api
class TestApiKeyListAPI:
    """Test cases for listing API keys."""

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, app, db_session):
        """Test listing API keys when none configured."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert data["api_keys"] == []

    @pytest.mark.asyncio
    async def test_list_api_keys(self, app, db_session):
        """Test listing configured API keys."""
        # Create an API key - encrypted_key is LargeBinary so use bytes
        api_key = ApiKey(
            provider="openai",
            encrypted_key=b"encrypted_data",
        )
        db_session.add(api_key)
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) == 1
        assert data["api_keys"][0]["provider"] == "openai"
        assert data["api_keys"][0]["is_configured"] is True
        # Should not expose actual key
        assert "encrypted_key" not in data["api_keys"][0]


@pytest.mark.api
class TestApiKeySetAPI:
    """Test cases for setting API keys."""

    @pytest.mark.asyncio
    async def test_set_api_key_new(self, app, db_session):
        """Test setting a new API key."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"encrypted_key_data"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/settings/api-keys",
                    json={"provider": "openai", "api_key": "sk-test123"},
                )

            assert response.status_code == 201
            data = response.json()
            assert "openai" in data["message"]

            # Verify key was saved
            query = select(ApiKey).where(ApiKey.provider == "openai")
            result = await db_session.execute(query)
            saved_key = result.scalar_one_or_none()
            assert saved_key is not None
            assert saved_key.encrypted_key == b"encrypted_key_data"

    @pytest.mark.asyncio
    async def test_set_api_key_update_existing(self, app, db_session):
        """Test updating an existing API key."""
        # Create existing key - use bytes for LargeBinary
        existing = ApiKey(
            provider="anthropic",
            encrypted_key=b"old_encrypted_key",
        )
        db_session.add(existing)
        await db_session.commit()

        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.return_value = b"new_encrypted_key"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/settings/api-keys",
                    json={"provider": "anthropic", "api_key": "sk-new-key"},
                )

            assert response.status_code == 201

            # Verify key was updated
            query = select(ApiKey).where(ApiKey.provider == "anthropic")
            result = await db_session.execute(query)
            updated_key = result.scalar_one()
            assert updated_key.encrypted_key == b"new_encrypted_key"

    @pytest.mark.asyncio
    async def test_set_api_key_encryption_error(self, app, db_session):
        """Test handling encryption error."""
        with patch("app.api.routes.settings.get_encryption_service") as mock_enc:
            mock_enc.return_value.encrypt.side_effect = Exception("Encryption failed")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/settings/api-keys", json={"provider": "openai", "api_key": "sk-test"}
                )

            assert response.status_code == 400
            assert "encrypt" in response.json()["detail"].lower()


@pytest.mark.api
class TestApiKeyDeleteAPI:
    """Test cases for deleting API keys."""

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, app, db_session):
        """Test deleting non-existent API key."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/settings/api-keys/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, app, db_session):
        """Test successful API key deletion."""
        # Create key to delete - use bytes
        api_key = ApiKey(
            provider="openai",
            encrypted_key=b"encrypted_data",
        )
        db_session.add(api_key)
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/settings/api-keys/openai")

        assert response.status_code == 204

        # Verify key was deleted
        query = select(ApiKey).where(ApiKey.provider == "openai")
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()
        assert deleted is None


@pytest.mark.api
class TestApiKeyTestAPI:
    """Test cases for testing API keys."""

    @pytest.mark.asyncio
    async def test_test_api_key_valid(self, app, db_session):
        """Test validating a working API key."""
        # Patch at the import location in the function
        with patch("app.core.llm.provider.LLMProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate = AsyncMock(return_value="Hi there!")
            mock_provider.return_value = mock_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/settings/api-keys/test",
                    json={"provider": "openai", "api_key": "sk-valid"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_test_api_key_invalid(self, app, db_session):
        """Test validating an invalid API key."""
        with patch("app.core.llm.provider.LLMProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate = AsyncMock(side_effect=Exception("Invalid API key"))
            mock_provider.return_value = mock_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/settings/api-keys/test",
                    json={"provider": "openai", "api_key": "sk-invalid"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "failed" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_api_key_different_providers(self, app, db_session):
        """Test API key validation for different providers."""
        providers = ["openai", "anthropic", "azure"]

        for provider in providers:
            with patch("app.core.llm.provider.LLMProvider") as mock_provider:
                mock_instance = MagicMock()
                mock_instance.generate = AsyncMock(return_value="Response")
                mock_provider.return_value = mock_instance

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/settings/api-keys/test",
                        json={"provider": provider, "api_key": f"key-{provider}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is True
