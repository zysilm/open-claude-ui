"""LiteLLM provider and model discovery utilities."""

from typing import Optional
import litellm
from functools import lru_cache


# Provider display names and API key environment variable mappings
PROVIDER_METADATA = {
    "openai": {"name": "OpenAI", "env_key": "OPENAI_API_KEY"},
    "anthropic": {"name": "Anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "azure": {"name": "Azure OpenAI", "env_key": "AZURE_API_KEY"},
    "cohere": {"name": "Cohere", "env_key": "COHERE_API_KEY"},
    "huggingface": {"name": "Hugging Face", "env_key": "HUGGINGFACE_API_KEY"},
    "together_ai": {"name": "Together AI", "env_key": "TOGETHER_API_KEY"},
    "groq": {"name": "Groq", "env_key": "GROQ_API_KEY"},
    "mistral": {"name": "Mistral AI", "env_key": "MISTRAL_API_KEY"},
    "gemini": {"name": "Google Gemini", "env_key": "GEMINI_API_KEY"},
    "vertex_ai": {"name": "Google Vertex AI", "env_key": "GOOGLE_APPLICATION_CREDENTIALS"},
    "bedrock": {"name": "AWS Bedrock", "env_key": "AWS_ACCESS_KEY_ID"},
    "ollama": {"name": "Ollama (Local)", "env_key": None},
    "openrouter": {"name": "OpenRouter", "env_key": "OPENROUTER_API_KEY"},
    "deepseek": {"name": "DeepSeek", "env_key": "DEEPSEEK_API_KEY"},
    "fireworks_ai": {"name": "Fireworks AI", "env_key": "FIREWORKS_API_KEY"},
    "perplexity": {"name": "Perplexity", "env_key": "PERPLEXITYAI_API_KEY"},
    "replicate": {"name": "Replicate", "env_key": "REPLICATE_API_KEY"},
    "ai21": {"name": "AI21 Labs", "env_key": "AI21_API_KEY"},
    "xai": {"name": "xAI (Grok)", "env_key": "XAI_API_KEY"},
}

# Commonly used providers to show first in the UI
FEATURED_PROVIDERS = [
    "openai",
    "anthropic",
    "azure",
    "gemini",
    "mistral",
    "groq",
    "together_ai",
    "cohere",
    "deepseek",
    "ollama",
    "openrouter",
    "bedrock",
]

# Model name patterns to exclude (non-chat models)
EXCLUDE_PATTERNS = [
    "embed",
    "dall-e",
    "whisper",
    "tts",
    "rerank",
    "moderation",
    "realtime",
    "audio",
    "vision-preview",  # Exclude some specialized vision models
    "gpt-image",  # Image generation models
    "image-",
    "/image",
    "canvas",
    "nova-canvas",
    "stable-diffusion",
    "stability.",
    "x-1024",  # Image resolution patterns
    "1024-x-",
    "512-x-",
    "256-x-",
    "/50-steps",  # Image generation steps
    "/max-steps",
]


def _is_chat_model(model_name: str) -> bool:
    """Check if a model is a chat/completion model (not embedding, image, etc.)."""
    model_lower = model_name.lower()
    return not any(pattern in model_lower for pattern in EXCLUDE_PATTERNS)


def _format_model_name(model_id: str, provider: str) -> str:
    """Create a display name for a model."""
    # Remove provider prefix if present (e.g., "groq/llama-3.1-8b" -> "llama-3.1-8b")
    name = model_id
    if "/" in name:
        parts = name.split("/")
        # Handle cases like "azure/eu/gpt-4o" or "groq/llama-3.1-8b"
        name = parts[-1] if len(parts) <= 2 else "/".join(parts[1:])

    # Clean up common prefixes
    prefixes_to_remove = ["ft:", "azure/"]
    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix) :]

    return name


def get_provider_models(provider: str) -> list[dict]:
    """
    Get available chat models for a specific provider from LiteLLM.

    Args:
        provider: Provider identifier (e.g., 'openai', 'anthropic')

    Returns:
        List of model dicts with 'id' and 'name' keys
    """
    if not hasattr(litellm, "models_by_provider"):
        return []

    provider_models = litellm.models_by_provider.get(provider, set())
    if not provider_models:
        return []

    models = []
    seen_names = set()

    for model_id in sorted(provider_models):
        if not _is_chat_model(model_id):
            continue

        name = _format_model_name(model_id, provider)

        # Skip duplicates by display name
        if name in seen_names:
            continue
        seen_names.add(name)

        models.append({"id": model_id, "name": name})

    # Sort by name for better UX
    return sorted(models, key=lambda m: m["name"])


def get_available_providers(featured_only: bool = False) -> list[dict]:
    """
    Get list of available LLM providers from LiteLLM.

    Args:
        featured_only: If True, only return commonly-used providers

    Returns:
        List of provider dicts with id, name, models, and env_key
    """
    providers = []

    # Get all provider IDs from LiteLLM
    litellm_providers = set()
    if hasattr(litellm, "provider_list"):
        for p in litellm.provider_list:
            provider_id = p.value if hasattr(p, "value") else str(p)
            litellm_providers.add(provider_id)

    # Determine which providers to include
    if featured_only:
        provider_ids = [p for p in FEATURED_PROVIDERS if p in litellm_providers]
    else:
        # Featured first, then others alphabetically
        featured = [p for p in FEATURED_PROVIDERS if p in litellm_providers]
        others = sorted([p for p in litellm_providers if p not in FEATURED_PROVIDERS])
        provider_ids = featured + others

    for provider_id in provider_ids:
        # Get models for this provider
        models = get_provider_models(provider_id)

        # Skip providers with no chat models
        if not models:
            continue

        # Get metadata
        metadata = PROVIDER_METADATA.get(provider_id, {})
        name = metadata.get("name", provider_id.replace("_", " ").title())
        env_key = metadata.get("env_key")

        providers.append(
            {
                "id": provider_id,
                "name": name,
                "models": models,
                "env_key": env_key,
            }
        )

    return providers


@lru_cache(maxsize=1)
def get_cached_providers() -> list[dict]:
    """
    Get cached list of featured providers.
    Cached to avoid repeated LiteLLM lookups.
    """
    return get_available_providers(featured_only=True)


def get_default_model_for_provider(provider: str) -> Optional[str]:
    """
    Get a sensible default model for a provider.

    Args:
        provider: Provider identifier

    Returns:
        Default model ID or None if no models available
    """
    defaults = {
        "openai": "gpt-5-mini",
        "anthropic": "claude-3-5-sonnet-latest",
        "azure": "gpt-5-mini",
        "gemini": "gemini/gemini-1.5-flash",
        "mistral": "mistral/mistral-small-latest",
        "groq": "groq/llama-3.1-8b-instant",
        "together_ai": "together_ai/meta-llama/Llama-3-8b-chat-hf",
        "cohere": "command-r",
        "deepseek": "deepseek/deepseek-chat",
        "ollama": "ollama/llama3.1",
    }

    if provider in defaults:
        return defaults[provider]

    # Fall back to first available model
    models = get_provider_models(provider)
    return models[0]["id"] if models else None


def get_test_model_for_provider(provider: str) -> str:
    """
    Get a cheap/fast model for testing API keys.

    Args:
        provider: Provider identifier

    Returns:
        Model ID suitable for testing
    """
    test_models = {
        "openai": "gpt-5-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "azure": "gpt-5-mini",
        "gemini": "gemini/gemini-1.5-flash",
        "mistral": "mistral/mistral-small-latest",
        "groq": "groq/llama-3.1-8b-instant",
        "together_ai": "together_ai/meta-llama/Llama-3-8b-chat-hf",
        "cohere": "command-light",
        "deepseek": "deepseek/deepseek-chat",
    }

    return test_models.get(provider, get_default_model_for_provider(provider) or "gpt-5-mini")
