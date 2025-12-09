"""Tests for ThinkTool."""

import pytest

from app.core.agent.tools.think_tool import ThinkTool


@pytest.mark.unit
class TestThinkTool:
    """Test cases for ThinkTool."""

    def test_tool_properties(self):
        """Test ThinkTool properties."""
        tool = ThinkTool()

        assert tool.name == "think"
        assert (
            "structured thinking" in tool.description.lower() or "think" in tool.description.lower()
        )
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "thought"
        assert tool.parameters[0].required is True

    @pytest.mark.asyncio
    async def test_execute_simple_thought(self):
        """Test executing a simple thought."""
        tool = ThinkTool()
        result = await tool.execute(thought="Let me analyze this problem step by step.")

        assert result.success is True
        assert "recorded" in result.output.lower() or "continue" in result.output.lower()
        assert "thought_length" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_complex_thought(self):
        """Test executing a complex multi-line thought."""
        tool = ThinkTool()
        complex_thought = """
        Let me analyze the error:
        1. The error occurs on line 15
        2. The issue is a missing import
        3. I need to add 'import json' at the top

        Next steps:
        - Read the file first
        - Add the import
        - Verify the fix
        """
        result = await tool.execute(thought=complex_thought)

        assert result.success is True
        assert result.metadata["thought_length"] == len(complex_thought)

    @pytest.mark.asyncio
    async def test_execute_empty_thought(self):
        """Test executing an empty thought."""
        tool = ThinkTool()
        result = await tool.execute(thought="")

        assert result.success is True
        assert result.metadata["thought_length"] == 0

    @pytest.mark.asyncio
    async def test_no_side_effects(self):
        """Test that think tool has no side effects."""
        tool = ThinkTool()

        # Execute multiple thoughts
        result1 = await tool.execute(thought="First thought")
        result2 = await tool.execute(thought="Second thought")

        # Each should succeed independently
        assert result1.success is True
        assert result2.success is True

    def test_tool_definition_format(self):
        """Test tool definition format for LLM."""
        tool = ThinkTool()
        formatted = tool.format_for_llm()

        assert formatted["type"] == "function"
        assert formatted["function"]["name"] == "think"
        assert "thought" in formatted["function"]["parameters"]["properties"]
        assert "thought" in formatted["function"]["parameters"]["required"]
