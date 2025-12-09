"""Tests for base Tool classes and ToolRegistry."""

import pytest
from pydantic import BaseModel, Field

from app.core.agent.tools.base import (
    Tool,
    ToolParameter,
    ToolDefinition,
    ToolResult,
    ToolRegistry,
)


@pytest.mark.unit
class TestToolParameter:
    """Test cases for ToolParameter."""

    def test_create_required_parameter(self):
        """Test creating a required parameter."""
        param = ToolParameter(
            name="command",
            type="string",
            description="The command to execute",
            required=True,
        )
        assert param.name == "command"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None

    def test_create_optional_parameter(self):
        """Test creating an optional parameter with default."""
        param = ToolParameter(
            name="timeout",
            type="number",
            description="Timeout in seconds",
            required=False,
            default=30,
        )
        assert param.name == "timeout"
        assert param.required is False
        assert param.default == 30


@pytest.mark.unit
class TestToolDefinition:
    """Test cases for ToolDefinition."""

    def test_create_tool_definition(self):
        """Test creating a tool definition."""
        params = [
            ToolParameter(name="path", type="string", description="File path", required=True),
        ]
        definition = ToolDefinition(
            name="file_read",
            description="Read a file",
            parameters=params,
        )
        assert definition.name == "file_read"
        assert definition.description == "Read a file"
        assert len(definition.parameters) == 1


@pytest.mark.unit
class TestToolResult:
    """Test cases for ToolResult."""

    def test_success_result(self):
        """Test successful tool result."""
        result = ToolResult(success=True, output="Operation completed")
        assert result.success is True
        assert result.output == "Operation completed"
        assert result.error is None
        assert result.metadata == {}
        assert result.is_validation_error is False

    def test_error_result(self):
        """Test error tool result."""
        result = ToolResult(
            success=False,
            output="",
            error="File not found",
        )
        assert result.success is False
        assert result.error == "File not found"

    def test_result_with_metadata(self):
        """Test tool result with metadata."""
        result = ToolResult(
            success=True,
            output="Done",
            metadata={"exit_code": 0, "duration": 1.5},
        )
        assert result.metadata["exit_code"] == 0
        assert result.metadata["duration"] == 1.5

    def test_validation_error_result(self):
        """Test validation error result."""
        result = ToolResult(
            success=False,
            output="",
            error="Invalid parameter",
            is_validation_error=True,
        )
        assert result.is_validation_error is True


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self):
        return [
            ToolParameter(name="input", type="string", description="Input value", required=True),
            ToolParameter(
                name="optional",
                type="number",
                description="Optional value",
                required=False,
                default=10,
            ),
        ]

    async def execute(self, input: str, optional: int = 10, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            output=f"Executed with input={input}, optional={optional}",
        )


class MockToolWithSchema(Tool):
    """Mock tool with Pydantic input schema."""

    class InputSchema(BaseModel):
        value: str = Field(min_length=1)
        count: int = Field(ge=0)

    @property
    def name(self) -> str:
        return "mock_schema_tool"

    @property
    def description(self) -> str:
        return "A mock tool with schema validation"

    @property
    def parameters(self):
        return [
            ToolParameter(name="value", type="string", description="Value", required=True),
            ToolParameter(name="count", type="number", description="Count", required=True),
        ]

    @property
    def input_schema(self):
        return self.InputSchema

    async def execute(self, value: str, count: int, **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"value={value}, count={count}")


@pytest.mark.unit
class TestTool:
    """Test cases for Tool base class."""

    def test_get_definition(self):
        """Test getting tool definition."""
        tool = MockTool()
        definition = tool.get_definition()

        assert definition.name == "mock_tool"
        assert definition.description == "A mock tool for testing"
        assert len(definition.parameters) == 2

    def test_format_for_llm(self):
        """Test formatting tool for LLM function calling."""
        tool = MockTool()
        formatted = tool.format_for_llm()

        assert formatted["type"] == "function"
        assert formatted["function"]["name"] == "mock_tool"
        assert "parameters" in formatted["function"]
        assert formatted["function"]["parameters"]["type"] == "object"
        assert "input" in formatted["function"]["parameters"]["properties"]
        assert "optional" in formatted["function"]["parameters"]["properties"]
        assert "input" in formatted["function"]["parameters"]["required"]
        assert "optional" not in formatted["function"]["parameters"]["required"]

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test tool execution."""
        tool = MockTool()
        result = await tool.execute(input="test", optional=20)

        assert result.success is True
        assert "input=test" in result.output
        assert "optional=20" in result.output

    @pytest.mark.asyncio
    async def test_validate_and_execute_without_schema(self):
        """Test validate_and_execute without input schema."""
        tool = MockTool()
        result = await tool.validate_and_execute(input="test")

        assert result.success is True
        assert "input=test" in result.output

    @pytest.mark.asyncio
    async def test_validate_and_execute_with_schema_valid(self):
        """Test validate_and_execute with valid input schema."""
        tool = MockToolWithSchema()
        result = await tool.validate_and_execute(value="test", count=5)

        assert result.success is True
        assert "value=test" in result.output

    @pytest.mark.asyncio
    async def test_validate_and_execute_with_schema_invalid(self):
        """Test validate_and_execute with invalid input schema."""
        tool = MockToolWithSchema()
        result = await tool.validate_and_execute(value="", count=-1)

        assert result.success is False
        assert result.is_validation_error is True
        assert "validation failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validate_and_execute_handles_execution_error(self):
        """Test that execution errors are caught."""

        class ErrorTool(MockTool):
            async def execute(self, **kwargs):
                raise Exception("Execution failed")

        tool = ErrorTool()
        result = await tool.validate_and_execute(input="test")

        assert result.success is False
        assert "execution error" in result.error.lower()


@pytest.mark.unit
class TestToolRegistry:
    """Test cases for ToolRegistry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert registry.has_tool("mock_tool")
        assert registry.get("mock_tool") == tool

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)
        registry.unregister("mock_tool")

        assert not registry.has_tool("mock_tool")
        assert registry.get("mock_tool") is None

    def test_unregister_nonexistent_tool(self):
        """Test unregistering a nonexistent tool doesn't raise."""
        registry = ToolRegistry()
        registry.unregister("nonexistent")  # Should not raise

    def test_get_nonexistent_tool(self):
        """Test getting a nonexistent tool returns None."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockToolWithSchema()

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "mock_tool" in tool_names
        assert "mock_schema_tool" in tool_names

    def test_has_tool(self):
        """Test checking if tool exists."""
        registry = ToolRegistry()
        tool = MockTool()

        assert not registry.has_tool("mock_tool")
        registry.register(tool)
        assert registry.has_tool("mock_tool")

    def test_get_tools_for_llm(self):
        """Test getting tools formatted for LLM."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockToolWithSchema()

        registry.register(tool1)
        registry.register(tool2)

        llm_tools = registry.get_tools_for_llm()

        assert len(llm_tools) == 2
        for tool_def in llm_tools:
            assert tool_def["type"] == "function"
            assert "function" in tool_def
            assert "name" in tool_def["function"]
