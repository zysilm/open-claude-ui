"""Tests for ApiKey database model."""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.database import ApiKey


@pytest.mark.unit
class TestApiKeyModel:
    """Test cases for the ApiKey model."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, db_session):
        """Test creating a new API key record."""
        api_key = ApiKey(
            provider="openai",
            encrypted_key=b"encrypted_key_bytes",
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.id is not None
        assert len(api_key.id) == 36
        assert api_key.provider == "openai"
        assert api_key.encrypted_key == b"encrypted_key_bytes"
        assert isinstance(api_key.created_at, datetime)
        assert api_key.last_used_at is None

    @pytest.mark.asyncio
    async def test_api_key_provider_unique(self, db_session):
        """Test that provider is unique."""
        api_key1 = ApiKey(
            provider="openai",
            encrypted_key=b"key1",
        )
        db_session.add(api_key1)
        await db_session.commit()

        api_key2 = ApiKey(
            provider="openai",
            encrypted_key=b"key2",
        )
        db_session.add(api_key2)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_different_providers(self, db_session):
        """Test storing keys for different providers."""
        providers = ["openai", "anthropic", "azure", "cohere"]

        for provider in providers:
            api_key = ApiKey(
                provider=provider,
                encrypted_key=f"encrypted_{provider}".encode(),
            )
            db_session.add(api_key)

        await db_session.commit()

        query = select(ApiKey)
        result = await db_session.execute(query)
        all_keys = result.scalars().all()

        assert len(all_keys) == 4
        stored_providers = {key.provider for key in all_keys}
        assert stored_providers == set(providers)

    @pytest.mark.asyncio
    async def test_last_used_at_update(self, db_session):
        """Test updating last_used_at timestamp."""
        api_key = ApiKey(
            provider="openai",
            encrypted_key=b"test_key",
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.last_used_at is None

        # Update last_used_at
        api_key.last_used_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.last_used_at is not None
        assert isinstance(api_key.last_used_at, datetime)

    @pytest.mark.asyncio
    async def test_encrypted_key_binary(self, db_session):
        """Test that encrypted_key stores binary data correctly."""
        # Simulate a Fernet encrypted key
        encrypted_data = b"gAAAAABj..." + bytes(range(256))

        api_key = ApiKey(
            provider="test_provider",
            encrypted_key=encrypted_data,
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.encrypted_key == encrypted_data
        assert isinstance(api_key.encrypted_key, bytes)

    @pytest.mark.asyncio
    async def test_query_by_provider(self, db_session):
        """Test querying API key by provider."""
        api_key = ApiKey(
            provider="anthropic",
            encrypted_key=b"anthropic_key",
        )
        db_session.add(api_key)
        await db_session.commit()

        query = select(ApiKey).where(ApiKey.provider == "anthropic")
        result = await db_session.execute(query)
        fetched = result.scalar_one_or_none()

        assert fetched is not None
        assert fetched.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_delete_api_key(self, db_session):
        """Test deleting an API key."""
        api_key = ApiKey(
            provider="to_delete",
            encrypted_key=b"delete_me",
        )
        db_session.add(api_key)
        await db_session.commit()

        key_id = api_key.id
        await db_session.delete(api_key)
        await db_session.commit()

        query = select(ApiKey).where(ApiKey.id == key_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()

        assert deleted is None
