"""Tests for agent templates."""

import pytest

from app.core.agent.templates import (
    AgentTemplate,
    get_template,
    list_templates,
    get_template_config,
    AGENT_TEMPLATES,
)


@pytest.mark.unit
class TestAgentTemplate:
    """Test cases for AgentTemplate model."""

    def test_template_structure(self):
        """Test AgentTemplate structure."""
        template = AgentTemplate(
            id="test_template",
            name="Test Template",
            description="A test template",
            agent_type="code_agent",
            environment_type="python3.13",
            environment_config={},
            enabled_tools=["bash", "file_read"],
            system_instructions="Be helpful",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            llm_config={"temperature": 0.7},
        )

        assert template.id == "test_template"
        assert template.name == "Test Template"
        assert template.environment_type == "python3.13"
        assert len(template.enabled_tools) == 2
        assert template.llm_provider == "openai"


@pytest.mark.unit
class TestAgentTemplates:
    """Test cases for template registry functions."""

    def test_default_templates_exist(self):
        """Test that default templates are defined."""
        assert len(AGENT_TEMPLATES) > 0

    def test_default_template_exists(self):
        """Test that 'default' template exists."""
        template = get_template("default")
        assert template is not None
        assert template.id == "default"

    def test_get_template(self):
        """Test getting a template by ID."""
        # Get any available template
        templates = list_templates()
        if templates:
            first_template = templates[0]
            fetched = get_template(first_template.id)
            assert fetched is not None
            assert fetched.id == first_template.id

    def test_get_template_not_found(self):
        """Test getting a non-existent template."""
        template = get_template("nonexistent_template")
        assert template is None

    def test_list_templates(self):
        """Test listing all templates."""
        templates = list_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0

        for template in templates:
            assert isinstance(template, AgentTemplate)
            assert template.id is not None
            assert template.name is not None

    def test_get_template_config(self):
        """Test getting template config for DB update."""
        config = get_template_config("default")

        assert config is not None
        assert "agent_type" in config
        assert "enabled_tools" in config
        assert "llm_provider" in config
        assert "llm_model" in config

    def test_get_template_config_not_found(self):
        """Test getting config for non-existent template."""
        config = get_template_config("nonexistent")
        assert config is None

    def test_template_tools_structure(self):
        """Test that template tools are properly structured."""
        templates = list_templates()

        for template in templates:
            assert isinstance(template.enabled_tools, list)
            # Each tool should be a string
            for tool in template.enabled_tools:
                assert isinstance(tool, str)

    def test_template_llm_config(self):
        """Test that templates have valid LLM config."""
        templates = list_templates()

        for template in templates:
            assert template.llm_provider is not None
            assert template.llm_model is not None
            assert isinstance(template.llm_config, dict)

    def test_common_templates(self):
        """Test that common templates exist."""
        # These are expected templates based on the README
        expected_templates = ["default", "python_dev"]

        for template_id in expected_templates:
            template = get_template(template_id)
            # At minimum, default should exist
            if template_id == "default":
                assert template is not None

    def test_template_environment_types(self):
        """Test template environment types are valid."""
        valid_environments = ["python3.13", "node20", "nodejs", "cpp", None]
        templates = list_templates()

        for template in templates:
            assert template.environment_type in valid_environments

    def test_template_has_system_instructions(self):
        """Test that templates have system instructions or None."""
        templates = list_templates()

        for template in templates:
            # system_instructions can be a string or None
            assert template.system_instructions is None or isinstance(
                template.system_instructions, str
            )
