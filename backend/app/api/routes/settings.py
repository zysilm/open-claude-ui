"""Settings API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.storage.database import get_db
from app.core.security.encryption import get_encryption_service
from app.core.llm.providers import (
    get_available_providers,
    get_test_model_for_provider,
)
from app.models.database import ApiKey
from app.models.schemas.settings import (
    ApiKeyCreate,
    ApiKeyTest,
    ApiKeyStatus,
    ApiKeyListResponse,
    LLMModel,
    LLMProviderInfo,
    LLMProvidersResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    # FUTURE: current_user: User = Depends(get_current_user)
):
    """
    List all configured API keys (without exposing actual keys).

    Returns status information for each provider.
    """
    # FUTURE: Add .where(ApiKey.user_id == current_user.id)
    query = select(ApiKey)
    result = await db.execute(query)
    keys = result.scalars().all()

    return ApiKeyListResponse(
        api_keys=[
            ApiKeyStatus(
                provider=key.provider,
                is_configured=True,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                created_at=key.created_at.isoformat(),
            )
            for key in keys
        ]
    )


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def set_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    # FUTURE: current_user: User = Depends(get_current_user)
):
    """
    Set or update an API key for a provider.

    The key will be encrypted before storage and never returned in responses.
    """
    encryption_service = get_encryption_service()

    # Encrypt the API key
    try:
        encrypted_key = encryption_service.encrypt(key_data.api_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to encrypt API key: {str(e)}",
        )

    # Check if key already exists for this provider
    # FUTURE: Add .where(ApiKey.user_id == current_user.id)
    query = select(ApiKey).where(ApiKey.provider == key_data.provider)
    result = await db.execute(query)
    existing_key = result.scalar_one_or_none()

    if existing_key:
        # Update existing key
        existing_key.encrypted_key = encrypted_key
        existing_key.created_at = datetime.utcnow()
        existing_key.last_used_at = None
    else:
        # Create new key
        new_key = ApiKey(
            provider=key_data.provider,
            encrypted_key=encrypted_key,
            # FUTURE: user_id=current_user.id
        )
        db.add(new_key)

    await db.commit()

    return {"message": f"API key for {key_data.provider} saved successfully"}


@router.delete("/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    provider: str,
    db: AsyncSession = Depends(get_db),
    # FUTURE: current_user: User = Depends(get_current_user)
):
    """Delete an API key for a provider."""
    # FUTURE: Add .where(ApiKey.user_id == current_user.id)
    stmt = delete(ApiKey).where(ApiKey.provider == provider)
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for provider: {provider}",
        )


@router.post("/api-keys/test")
async def test_api_key(
    test_data: ApiKeyTest,
):
    """
    Test an API key before saving it.

    Makes a lightweight API call to verify the key is valid.
    Uses LiteLLM's model database to pick appropriate test models.
    """
    from app.core.llm.provider import LLMProvider

    try:
        # Get appropriate test model from LiteLLM provider database
        model = get_test_model_for_provider(test_data.provider)

        provider = LLMProvider(
            provider=test_data.provider,
            model=model,
            api_key=test_data.api_key,
            temperature=0.1,
            max_tokens=10,
        )

        # Try a simple completion to test the key
        await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            stream=False,
        )

        # If we get here, the key works
        return {
            "valid": True,
            "message": f"API key for {test_data.provider} is valid",
        }

    except Exception as e:
        return {
            "valid": False,
            "message": f"API key validation failed: {str(e)}",
        }


@router.get("/llm-providers", response_model=LLMProvidersResponse)
async def list_llm_providers(
    featured_only: bool = Query(
        True, description="Only return commonly-used providers (faster, less noise)"
    ),
):
    """
    Get available LLM providers and their models from LiteLLM.

    This endpoint dynamically queries LiteLLM's model database to return
    all supported providers and their available models. Use this to populate
    provider/model selection dropdowns in the UI.

    Args:
        featured_only: If True (default), only returns popular providers like
                      OpenAI, Anthropic, Azure, etc. Set to False to get all
                      100+ providers supported by LiteLLM.

    Returns:
        List of providers with their available models
    """
    providers_data = get_available_providers(featured_only=featured_only)

    providers = [
        LLMProviderInfo(
            id=p["id"],
            name=p["name"],
            models=[LLMModel(id=m["id"], name=m["name"]) for m in p["models"]],
            env_key=p.get("env_key"),
        )
        for p in providers_data
    ]

    return LLMProvidersResponse(providers=providers)
