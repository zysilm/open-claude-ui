"""Tests for LLM Provider."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm.provider import (
    LLMProvider,
    create_llm_provider,
    create_llm_provider_with_db,
)


@pytest.mark.unit
class TestLLMProvider:
    """Test cases for LLMProvider."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        provider = LLMProvider()

        assert provider.provider == "openai"
        assert provider.model == "gpt-4"
        assert provider.api_key is None
        assert provider.config == {}

    def test_init_with_values(self):
        """Test initialization with custom values."""
        provider = LLMProvider(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key",
            temperature=0.7,
        )

        assert provider.provider == "anthropic"
        assert provider.model == "claude-3-opus"
        assert provider.api_key == "test-key"
        assert provider.config["temperature"] == 0.7

    def test_set_api_key_openai(self):
        """Test setting OpenAI API key in environment."""
        with patch.dict(os.environ, {}, clear=True):
            _provider = LLMProvider(provider="openai", api_key="sk-test-key")
            # API key should be set in environment
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"

    def test_set_api_key_anthropic(self):
        """Test setting Anthropic API key in environment."""
        with patch.dict(os.environ, {}, clear=True):
            _provider = LLMProvider(provider="anthropic", api_key="sk-ant-test-key")
            assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-key"

    def test_build_model_name_openai(self):
        """Test building model name for OpenAI."""
        provider = LLMProvider(provider="openai", model="gpt-4o")
        assert provider._build_model_name() == "gpt-4o"

    def test_build_model_name_other_providers(self):
        """Test building model name for other providers."""
        provider = LLMProvider(provider="anthropic", model="claude-3-opus")
        assert provider._build_model_name() == "anthropic/claude-3-opus"

        provider = LLMProvider(provider="azure", model="gpt-4")
        assert provider._build_model_name() == "azure/gpt-4"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        provider = LLMProvider()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]

        with patch("app.core.llm.provider.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            response = await provider.generate(messages=[{"role": "user", "content": "Hello"}])

            assert response == mock_response
            mock_acompletion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_stream(self):
        """Test generation with streaming."""
        provider = LLMProvider()

        with patch("app.core.llm.provider.acompletion", new_callable=AsyncMock) as mock_acompletion:
            await provider.generate(messages=[{"role": "user", "content": "Hello"}], stream=True)

            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["stream"] is True

    @pytest.mark.asyncio
    async def test_generate_exception(self):
        """Test generate handles exceptions."""
        provider = LLMProvider()

        with patch("app.core.llm.provider.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.side_effect = Exception("API error")

            with pytest.raises(Exception) as exc_info:
                await provider.generate(messages=[{"role": "user", "content": "Hello"}])

            assert "LLM generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        """Test streaming generation."""
        provider = LLMProvider()

        # Create mock streaming response
        async def mock_stream():
            for text in ["Hello", " ", "World"]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = text
                chunk.choices[0].delta.tool_calls = None
                yield chunk

        with patch("app.core.llm.provider.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            chunks = []
            async for chunk in provider.generate_stream(
                messages=[{"role": "user", "content": "Hello"}]
            ):
                chunks.append(chunk)

            assert chunks == ["Hello", " ", "World"]

    @pytest.mark.asyncio
    async def test_generate_stream_with_tools(self):
        """Test streaming generation with tools."""
        provider = LLMProvider()

        # Create mock streaming response with tool calls
        async def mock_stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = None

            tool_call = MagicMock()
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"
            tool_call.function.arguments = '{"arg": "value"}'
            tool_call.index = 0

            chunk.choices[0].delta.tool_calls = [tool_call]
            yield chunk

        with patch("app.core.llm.provider.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            tools = [{"type": "function", "function": {"name": "test_tool"}}]
            chunks = []
            async for chunk in provider.generate_stream(
                messages=[{"role": "user", "content": "Hello"}], tools=tools
            ):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "function_call" in chunks[0]
            assert chunks[0]["function_call"]["name"] == "test_tool"


@pytest.mark.unit
class TestCreateLLMProvider:
    """Test cases for create_llm_provider function."""

    def test_create_llm_provider(self):
        """Test creating LLM provider with factory function."""
        provider = create_llm_provider(
            provider="openai", model="gpt-4o", llm_config={"temperature": 0.5}, api_key="test-key"
        )

        assert provider.provider == "openai"
        assert provider.model == "gpt-4o"
        assert provider.api_key == "test-key"
        assert provider.config["temperature"] == 0.5

    def test_create_llm_provider_without_key(self):
        """Test creating LLM provider without API key."""
        provider = create_llm_provider(provider="openai", model="gpt-4o", llm_config={})

        assert provider.api_key is None


@pytest.mark.unit
class TestCreateLLMProviderWithDB:
    """Test cases for create_llm_provider_with_db function."""

    @pytest.mark.asyncio
    async def test_with_explicit_api_key(self, db_session):
        """Test with explicitly provided API key."""
        provider = await create_llm_provider_with_db(
            provider="openai", model="gpt-4o", llm_config={}, db=db_session, api_key="explicit-key"
        )

        assert provider.api_key == "explicit-key"

    @pytest.mark.asyncio
    async def test_fallback_without_db_key(self, db_session):
        """Test fallback when no DB key exists."""
        provider = await create_llm_provider_with_db(
            provider="openai", model="gpt-4o", llm_config={}, db=db_session
        )

        # Should return provider without API key (will use env var)
        assert provider is not None
        assert provider.api_key is None
