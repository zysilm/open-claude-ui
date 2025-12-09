"""Tests for UnifiedSearchTool."""

import pytest
from unittest.mock import AsyncMock

from app.core.agent.tools.search_tool_unified import (
    UnifiedSearchTool,
    PATTERN_SHORTCUTS,
    LANGUAGE_ALIASES,
)
from app.core.sandbox.container import SandboxContainer


@pytest.mark.unit
class TestUnifiedSearchTool:
    """Test cases for UnifiedSearchTool."""

    @pytest.fixture
    def mock_container(self, mock_docker_container):
        """Create a mock SandboxContainer for testing."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )
        container.execute = AsyncMock(return_value=(0, "", ""))
        return container

    def test_tool_properties(self, mock_container):
        """Test UnifiedSearchTool properties."""
        tool = UnifiedSearchTool(mock_container)

        assert tool.name == "search"
        assert "search" in tool.description.lower()
        assert len(tool.parameters) >= 3

        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "language" in param_names
        assert "path" in param_names

    def test_pattern_shortcuts(self):
        """Test pattern shortcuts are defined."""
        expected_shortcuts = ["functions", "classes", "imports", "tests", "methods"]

        for shortcut in expected_shortcuts:
            assert shortcut in PATTERN_SHORTCUTS

    def test_language_aliases(self):
        """Test language aliases."""
        assert LANGUAGE_ALIASES["py"] == "python"
        assert LANGUAGE_ALIASES["js"] == "javascript"
        assert LANGUAGE_ALIASES["ts"] == "typescript"

    def test_detect_mode_code(self, mock_container):
        """Test mode detection for code queries."""
        tool = UnifiedSearchTool(mock_container)

        assert tool._detect_mode("functions") == "code"
        assert tool._detect_mode("classes") == "code"
        assert tool._detect_mode("$NAME") == "code"

    def test_detect_mode_filename(self, mock_container):
        """Test mode detection for filename queries."""
        tool = UnifiedSearchTool(mock_container)

        assert tool._detect_mode("*.py") == "filename"
        assert tool._detect_mode("*.js") == "filename"
        assert tool._detect_mode("config.json") == "filename"

    def test_detect_mode_text(self, mock_container):
        """Test mode detection for text queries."""
        tool = UnifiedSearchTool(mock_container)

        assert tool._detect_mode("error message") == "text"
        assert tool._detect_mode("TODO") == "text"

    def test_normalize_language(self, mock_container):
        """Test language normalization."""
        tool = UnifiedSearchTool(mock_container)

        assert tool._normalize_language("py") == "python"
        assert tool._normalize_language("js") == "javascript"
        assert tool._normalize_language("Python") == "python"
        assert tool._normalize_language(None) is None

    def test_resolve_pattern(self, mock_container):
        """Test pattern resolution."""
        tool = UnifiedSearchTool(mock_container)

        # Shortcut resolution for Python
        pattern = tool._resolve_pattern("functions", "python")
        assert pattern == "def $NAME($$$)"

        # Shortcut resolution for JavaScript
        pattern = tool._resolve_pattern("functions", "javascript")
        assert pattern == "function $NAME($$$)"

        # Non-shortcut passes through
        pattern = tool._resolve_pattern("custom_pattern", "python")
        assert pattern == "custom_pattern"

    @pytest.mark.asyncio
    async def test_search_path_not_found(self, mock_container):
        """Test searching in non-existent path."""
        mock_container.execute.return_value = (1, "", "")
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="test", path="/workspace/nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_search_text(self, mock_container):
        """Test text search."""
        # Path exists
        mock_container.execute.side_effect = [
            (0, "exists", ""),  # Path check
            (0, "/workspace/out/file.py", ""),  # grep result
            (0, "5:TODO: fix this", ""),  # context
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="TODO", path="/workspace/out")

        assert result.success is True
        assert result.metadata["mode"] == "text"

    @pytest.mark.asyncio
    async def test_search_text_no_matches(self, mock_container):
        """Test text search with no matches."""
        mock_container.execute.side_effect = [
            (0, "exists", ""),  # Path check
            (1, "", ""),  # grep - no matches
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="nonexistent_string", path="/workspace/out")

        assert result.success is True
        assert "No files found" in result.output

    @pytest.mark.asyncio
    async def test_search_filename(self, mock_container):
        """Test filename search."""
        mock_container.execute.side_effect = [
            (0, "exists", ""),  # Path check
            (0, "/workspace/out/script.py\n/workspace/out/test.py", ""),  # find result
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="*.py", path="/workspace/out")

        assert result.success is True
        assert result.metadata["mode"] == "filename"
        assert result.metadata["matches"] == 2

    @pytest.mark.asyncio
    async def test_search_filename_no_matches(self, mock_container):
        """Test filename search with no matches."""
        mock_container.execute.side_effect = [
            (0, "exists", ""),  # Path check
            (0, "", ""),  # find - empty result
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="*.nonexistent", path="/workspace/out")

        assert result.success is True
        assert "No files found" in result.output

    @pytest.mark.asyncio
    async def test_search_code_requires_language(self, mock_container):
        """Test that code search shortcuts require language."""
        mock_container.execute.return_value = (0, "exists", "")
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(
            query="functions",
            path="/workspace/out",
            # No language specified
        )

        assert result.success is False
        assert "language" in result.error.lower()

    @pytest.mark.asyncio
    async def test_search_code_with_language(self, mock_container):
        """Test code search with language specified."""
        mock_container.execute.side_effect = [
            (0, "exists", ""),  # Path check
            (0, "", ""),  # ast-grep check - not installed
            (0, "/workspace/out/file.py", ""),  # fallback to text search
            (0, "10:def test_func():", ""),  # context
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="functions", language="python", path="/workspace/out")

        # Falls back to text search if ast-grep not available
        assert result.success is True

    @pytest.mark.asyncio
    async def test_search_with_max_results(self, mock_container):
        """Test search with max_results limit."""
        mock_container.execute.side_effect = [
            (0, "exists", ""),
            (0, "\n".join([f"/workspace/out/file{i}.py" for i in range(100)]), ""),
        ]
        tool = UnifiedSearchTool(mock_container)

        result = await tool.execute(query="*.py", path="/workspace/out", max_results=10)

        assert result.success is True

    def test_parse_ast_results_empty(self, mock_container):
        """Test parsing empty AST results."""
        tool = UnifiedSearchTool(mock_container)
        matches = tool._parse_ast_results("", 50)
        assert matches == []

    def test_parse_ast_results_json_array(self, mock_container):
        """Test parsing JSON array AST results."""
        tool = UnifiedSearchTool(mock_container)
        json_output = """[
            {"file": "test.py", "range": {"start": {"line": 10}}, "text": "def foo():"},
            {"file": "test.py", "range": {"start": {"line": 20}}, "text": "def bar():"}
        ]"""
        matches = tool._parse_ast_results(json_output, 50)

        assert len(matches) == 2
        assert matches[0]["file"] == "test.py"
        assert matches[0]["line"] == 10

    def test_format_code_results(self, mock_container):
        """Test formatting code search results."""
        tool = UnifiedSearchTool(mock_container)
        matches = [
            {"file": "/workspace/out/test.py", "line": 10, "match": "def foo():"},
            {"file": "/workspace/out/test.py", "line": 20, "match": "def bar():"},
        ]

        output = tool._format_code_results(matches, "functions", "def $NAME($$$)", 50)

        assert "2 match" in output
        assert "test.py" in output
        assert "Line 10" in output
        assert "Line 20" in output
