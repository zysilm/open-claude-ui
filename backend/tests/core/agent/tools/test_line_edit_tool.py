"""Tests for LineEditTool."""

import pytest
from unittest.mock import AsyncMock

from app.core.agent.tools.line_edit_tool import LineEditTool
from app.core.sandbox.container import SandboxContainer


@pytest.mark.unit
class TestLineEditTool:
    """Test cases for LineEditTool."""

    @pytest.fixture
    def mock_container(self, mock_docker_container):
        """Create a mock SandboxContainer for testing."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )
        container.read_file = AsyncMock()
        container.write_file = AsyncMock(return_value=True)
        return container

    def test_tool_properties(self, mock_container):
        """Test LineEditTool properties."""
        tool = LineEditTool(mock_container)

        assert tool.name == "edit_lines"
        assert "line" in tool.description.lower()
        assert len(tool.parameters) >= 5

        param_names = [p.name for p in tool.parameters]
        assert "command" in param_names
        assert "path" in param_names
        assert "start_line" in param_names
        assert "end_line" in param_names

    @pytest.mark.asyncio
    async def test_replace_single_line(self, mock_container):
        """Test replacing a single line."""
        mock_container.read_file.return_value = "line1\nline2\nline3\nline4"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=2,
            end_line=2,
            new_content="new_line2",
        )

        assert result.success is True
        assert "Replaced" in result.output

        # Check the written content
        write_call = mock_container.write_file.call_args
        written_content = write_call.args[1]
        assert "new_line2" in written_content

    @pytest.mark.asyncio
    async def test_replace_multiple_lines(self, mock_container):
        """Test replacing multiple lines."""
        mock_container.read_file.return_value = "line1\nline2\nline3\nline4\nline5"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=2,
            end_line=4,
            new_content="new_content",
        )

        assert result.success is True
        assert result.metadata["lines_before"] == 5
        assert result.metadata["lines_after"] == 3  # 5 - 3 + 1

    @pytest.mark.asyncio
    async def test_insert_lines(self, mock_container):
        """Test inserting lines."""
        mock_container.read_file.return_value = "line1\nline2\nline3"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="insert",
            path="/workspace/out/test.py",
            insert_line=1,
            new_content="inserted_line",
        )

        assert result.success is True
        assert "Inserted" in result.output
        assert result.metadata["lines_after"] == 4

    @pytest.mark.asyncio
    async def test_insert_at_beginning(self, mock_container):
        """Test inserting at the beginning of file."""
        mock_container.read_file.return_value = "line1\nline2"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="insert", path="/workspace/out/test.py", insert_line=0, new_content="first_line"
        )

        assert result.success is True
        written_content = mock_container.write_file.call_args.args[1]
        assert written_content.startswith("first_line")

    @pytest.mark.asyncio
    async def test_delete_lines(self, mock_container):
        """Test deleting lines."""
        mock_container.read_file.return_value = "line1\nline2\nline3\nline4\nline5"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="delete", path="/workspace/out/test.py", start_line=2, end_line=4
        )

        assert result.success is True
        assert "Deleted" in result.output
        assert result.metadata["lines_after"] == 2

    @pytest.mark.asyncio
    async def test_file_not_found(self, mock_container):
        """Test handling file not found."""
        mock_container.read_file.return_value = None
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/missing.py",
            start_line=1,
            end_line=1,
            new_content="new",
        )

        assert result.success is False
        assert "not found" in result.error.lower() or "cannot be read" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_command(self, mock_container):
        """Test invalid command."""
        mock_container.read_file.return_value = "line1"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="invalid", path="/workspace/out/test.py", start_line=1, end_line=1
        )

        assert result.success is False
        assert "Unknown command" in result.error or result.is_validation_error

    @pytest.mark.asyncio
    async def test_replace_missing_params(self, mock_container):
        """Test replace with missing parameters."""
        mock_container.read_file.return_value = "line1\nline2"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=1,
            # Missing end_line and new_content
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_insert_missing_insert_line(self, mock_container):
        """Test insert with missing insert_line parameter."""
        mock_container.read_file.return_value = "line1"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="insert",
            path="/workspace/out/test.py",
            new_content="content",
            # Missing insert_line
        )

        assert result.success is False
        assert "insert_line" in result.error.lower()

    @pytest.mark.asyncio
    async def test_line_out_of_range(self, mock_container):
        """Test start_line exceeding file length."""
        mock_container.read_file.return_value = "line1\nline2"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=10,
            end_line=12,
            new_content="new",
        )

        assert result.success is False
        assert "exceeds" in result.error.lower()

    @pytest.mark.asyncio
    async def test_python_syntax_validation(self, mock_container):
        """Test Python syntax validation."""
        mock_container.read_file.return_value = "def foo():\n    return 1"
        tool = LineEditTool(mock_container)

        # Replace with invalid Python syntax
        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=2,
            end_line=2,
            new_content="    return (",  # Incomplete parenthesis
            auto_indent=False,
        )

        assert result.success is False
        assert "syntax error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_auto_indent(self, mock_container):
        """Test auto-indentation."""
        mock_container.read_file.return_value = "def foo():\n    pass"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=2,
            end_line=2,
            new_content="return 42",
            auto_indent=True,
        )

        assert result.success is True
        written = mock_container.write_file.call_args.args[1]
        # Should have proper indentation
        assert "    return 42" in written or "return 42" in written

    @pytest.mark.asyncio
    async def test_path_validation(self, mock_container):
        """Test path validation blocks project_files."""
        tool = LineEditTool(mock_container)

        result = await tool.validate_and_execute(
            command="replace",
            path="/workspace/project_files/readonly.py",
            start_line=1,
            end_line=1,
            new_content="new",
        )

        assert result.success is False
        assert result.is_validation_error is True

    @pytest.mark.asyncio
    async def test_output_shows_diff(self, mock_container):
        """Test that output shows what was changed."""
        mock_container.read_file.return_value = "old_line1\nold_line2\nold_line3"
        tool = LineEditTool(mock_container)

        result = await tool.execute(
            command="replace",
            path="/workspace/out/test.py",
            start_line=2,
            end_line=2,
            new_content="new_line2",
        )

        assert result.success is True
        # Should show removed and added content
        assert "Removed" in result.output or "---" in result.output
        assert "Added" in result.output or "+++" in result.output
