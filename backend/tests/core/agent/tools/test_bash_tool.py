"""Tests for BashTool."""

import pytest
from unittest.mock import AsyncMock

from app.core.agent.tools.bash_tool import BashTool
from app.core.sandbox.container import SandboxContainer


@pytest.mark.unit
class TestBashTool:
    """Test cases for BashTool."""

    @pytest.fixture
    def mock_container(self, mock_docker_container):
        """Create a mock SandboxContainer for testing."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )
        # Make execute async
        container.execute = AsyncMock(return_value=(0, "output", ""))
        return container

    def test_tool_properties(self, mock_container):
        """Test BashTool properties."""
        tool = BashTool(mock_container)

        assert tool.name == "bash"
        assert "execute" in tool.description.lower()
        assert len(tool.parameters) == 3

        param_names = [p.name for p in tool.parameters]
        assert "command" in param_names
        assert "workdir" in param_names
        assert "timeout" in param_names

    def test_format_output_success(self, mock_container):
        """Test formatting successful output."""
        tool = BashTool(mock_container)
        output = tool._format_output(0, "file1.py\nfile2.py", "")

        assert "[SUCCESS]" in output
        assert "file1.py" in output
        assert "file2.py" in output
        assert "Execution successful" in output

    def test_format_output_success_with_stderr(self, mock_container):
        """Test formatting success with stderr (warnings)."""
        tool = BashTool(mock_container)
        output = tool._format_output(0, "result", "warning: deprecated")

        assert "[SUCCESS]" in output
        assert "result" in output
        assert "warning: deprecated" in output

    def test_format_output_error(self, mock_container):
        """Test formatting error output."""
        tool = BashTool(mock_container)
        output = tool._format_output(1, "", "command not found")

        assert "[ERROR]" in output
        assert "Exit code 1" in output
        assert "command not found" in output

    def test_format_output_no_output(self, mock_container):
        """Test formatting with no output."""
        tool = BashTool(mock_container)
        output = tool._format_output(0, "", "")

        assert "[SUCCESS]" in output
        assert "(no output)" in output

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_container):
        """Test executing a successful command."""
        mock_container.execute.return_value = (0, "hello world", "")
        tool = BashTool(mock_container)

        result = await tool.execute(command="echo 'hello world'")

        assert result.success is True
        assert "hello world" in result.output
        assert result.metadata["exit_code"] == 0
        mock_container.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_custom_workdir(self, mock_container):
        """Test executing with custom working directory."""
        mock_container.execute.return_value = (0, "", "")
        tool = BashTool(mock_container)

        await tool.execute(command="ls", workdir="/workspace/out")

        mock_container.execute.assert_called_once()
        call_kwargs = mock_container.execute.call_args.kwargs
        assert call_kwargs["workdir"] == "/workspace/out"

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, mock_container):
        """Test executing with custom timeout."""
        mock_container.execute.return_value = (0, "", "")
        tool = BashTool(mock_container)

        await tool.execute(command="long_running_command", timeout=60)

        mock_container.execute.assert_called_once()
        call_kwargs = mock_container.execute.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    @pytest.mark.asyncio
    async def test_execute_command_failure(self, mock_container):
        """Test executing a failing command."""
        mock_container.execute.return_value = (1, "", "bash: invalid_cmd: command not found")
        tool = BashTool(mock_container)

        result = await tool.execute(command="invalid_cmd")

        assert result.success is False
        assert result.metadata["exit_code"] == 1
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, mock_container):
        """Test handling of execution exceptions."""
        mock_container.execute.side_effect = Exception("Container error")
        tool = BashTool(mock_container)

        result = await tool.execute(command="ls")

        assert result.success is False
        assert "Failed to execute" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_command_blocked(self, mock_container):
        """Test that dangerous commands are blocked."""
        tool = BashTool(mock_container)

        # Pattern must match exactly - no space after semicolon
        result = await tool.execute(command="ls;rm -rf /")

        assert result.success is False
        assert "dangerous" in result.error.lower() or "Failed" in result.error

    @pytest.mark.asyncio
    async def test_safe_commands(self, mock_container):
        """Test various safe commands."""
        mock_container.execute.return_value = (0, "success", "")
        tool = BashTool(mock_container)

        safe_commands = [
            "ls -la",
            "python script.py",
            "pip install requests",
            "cat file.txt",
            "echo 'hello'",
            "pwd",
            "mkdir test_dir",
        ]

        for cmd in safe_commands:
            result = await tool.execute(command=cmd)
            assert result.success is True or "dangerous" not in str(result.error).lower()

    def test_llm_format(self, mock_container):
        """Test tool format for LLM."""
        tool = BashTool(mock_container)
        formatted = tool.format_for_llm()

        assert formatted["type"] == "function"
        assert formatted["function"]["name"] == "bash"
        props = formatted["function"]["parameters"]["properties"]
        assert "command" in props
        assert "workdir" in props
        assert "timeout" in props
