"""Tests for AgentConfiguration database model."""

import pytest
from sqlalchemy import select

from app.models.database import AgentConfiguration


@pytest.mark.unit
class TestAgentConfigurationModel:
    """Test cases for the AgentConfiguration model."""

    @pytest.mark.asyncio
    async def test_create_agent_config(self, db_session, sample_project):
        """Test creating a new agent configuration."""
        config = AgentConfiguration(
            project_id=sample_project.id,
            agent_type="code_agent",
            system_instructions="You are a helpful assistant.",
            enabled_tools=["bash", "file_read", "file_write"],
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            llm_config={"temperature": 0.7, "max_tokens": 4096},
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.id is not None
        assert len(config.id) == 36
        assert config.project_id == sample_project.id
        assert config.agent_type == "code_agent"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_agent_config_defaults(self, db_session, sample_project):
        """Test agent configuration default values."""
        config = AgentConfiguration(
            project_id=sample_project.id,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.agent_type == "code_agent"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.system_instructions is None

    @pytest.mark.asyncio
    async def test_enabled_tools_json(self, db_session, sample_project):
        """Test enabled_tools JSON field."""
        tools = ["bash", "file_read", "file_write", "edit_lines", "search", "think"]
        config = AgentConfiguration(
            project_id=sample_project.id,
            enabled_tools=tools,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.enabled_tools == tools
        assert len(config.enabled_tools) == 6
        assert "bash" in config.enabled_tools

    @pytest.mark.asyncio
    async def test_llm_config_json(self, db_session, sample_project):
        """Test llm_config JSON field."""
        llm_config = {
            "temperature": 0.8,
            "max_tokens": 8192,
            "top_p": 0.95,
            "frequency_penalty": 0.0,
        }
        config = AgentConfiguration(
            project_id=sample_project.id,
            llm_config=llm_config,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.llm_config["temperature"] == 0.8
        assert config.llm_config["max_tokens"] == 8192
        assert config.llm_config["top_p"] == 0.95

    @pytest.mark.asyncio
    async def test_agent_config_project_relationship(self, db_session, sample_project):
        """Test agent config relationship with project."""
        config = AgentConfiguration(
            project_id=sample_project.id,
            agent_type="data_analyst",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.project.id == sample_project.id
        assert config.project.name == sample_project.name

    @pytest.mark.asyncio
    async def test_update_agent_config(self, db_session, sample_agent_config):
        """Test updating an agent configuration."""
        sample_agent_config.llm_model = "gpt-4"
        sample_agent_config.llm_config = {"temperature": 0.5}
        await db_session.commit()
        await db_session.refresh(sample_agent_config)

        assert sample_agent_config.llm_model == "gpt-4"
        assert sample_agent_config.llm_config["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_system_instructions(self, db_session, sample_project):
        """Test system instructions field."""
        long_instructions = """
        You are a Python expert. Follow these guidelines:
        1. Write clean, readable code
        2. Include type hints
        3. Add docstrings to all functions
        4. Follow PEP 8 style guidelines
        """
        config = AgentConfiguration(
            project_id=sample_project.id,
            system_instructions=long_instructions,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert "Python expert" in config.system_instructions
        assert "PEP 8" in config.system_instructions

    @pytest.mark.asyncio
    async def test_different_providers(self, db_session, sample_project):
        """Test configuration with different LLM providers."""
        # Delete any existing config first
        existing_query = select(AgentConfiguration).where(
            AgentConfiguration.project_id == sample_project.id
        )
        existing_result = await db_session.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        if existing:
            await db_session.delete(existing)
            await db_session.commit()

        providers = [
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-opus"),
            ("azure", "gpt-4-turbo"),
        ]

        for provider, model in providers:
            # Clean up before each iteration
            existing_query = select(AgentConfiguration).where(
                AgentConfiguration.project_id == sample_project.id
            )
            existing_result = await db_session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            if existing:
                await db_session.delete(existing)
                await db_session.commit()

            config = AgentConfiguration(
                project_id=sample_project.id,
                llm_provider=provider,
                llm_model=model,
            )
            db_session.add(config)
            await db_session.commit()
            await db_session.refresh(config)

            assert config.llm_provider == provider
            assert config.llm_model == model
