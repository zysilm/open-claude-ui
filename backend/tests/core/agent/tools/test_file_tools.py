"""Tests for FileReadTool and FileWriteTool."""

import pytest
from unittest.mock import AsyncMock

from app.core.agent.tools.file_tools import FileReadTool, FileWriteTool
from app.core.sandbox.container import SandboxContainer


@pytest.mark.unit
class TestFileReadTool:
    """Test cases for FileReadTool."""

    @pytest.fixture
    def mock_container(self, mock_docker_container):
        """Create a mock SandboxContainer for testing."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )
        container.read_file = AsyncMock()
        return container

    def test_tool_properties(self, mock_container):
        """Test FileReadTool properties."""
        tool = FileReadTool(mock_container)

        assert tool.name == "file_read"
        assert "read" in tool.description.lower()
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "path"

    @pytest.mark.asyncio
    async def test_read_text_file(self, mock_container):
        """Test reading a text file."""
        mock_container.read_file.return_value = "print('Hello, World!')\n"
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/script.py")

        assert result.success is True
        assert "Hello, World" in result.output
        assert result.metadata["path"] == "/workspace/out/script.py"
        # Line numbers should be included
        assert "1:" in result.output

    @pytest.mark.asyncio
    async def test_read_file_with_line_numbers(self, mock_container):
        """Test that output includes line numbers."""
        mock_container.read_file.return_value = "line1\nline2\nline3"
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/test.txt")

        assert result.success is True
        assert "1:" in result.output
        assert "2:" in result.output
        assert "3:" in result.output
        assert result.metadata["line_count"] == 3

    @pytest.mark.asyncio
    async def test_read_image_file(self, mock_container):
        """Test reading an image file."""
        mock_container.read_file.return_value = "data:image/png;base64,iVBORw0KGgo..."
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/plot.png")

        assert result.success is True
        assert result.metadata["is_binary"] is True
        assert result.metadata["type"] == "image"
        assert "image_data" in result.metadata

    @pytest.mark.asyncio
    async def test_read_video_file(self, mock_container):
        """Test reading a video file - should not store binary data in metadata."""
        mock_container.read_file.return_value = "data:video/mp4;base64,AAAAIGZ0eXBpc29t..."
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/video.mp4")

        assert result.success is True
        assert result.metadata["is_binary"] is True
        assert result.metadata["type"] == "binary"
        assert result.metadata["mime_type"] == "video/mp4"
        assert result.metadata["filename"] == "video.mp4"
        # Should NOT store binary data in metadata to avoid bloating DB
        assert "data" not in result.metadata
        # LLM should get a short descriptive message, not the binary content
        assert "data:video/mp4;base64" not in result.output
        assert "binary file" in result.output.lower() or "video/mp4" in result.output

    @pytest.mark.asyncio
    async def test_read_audio_file(self, mock_container):
        """Test reading an audio file - should not store binary data in metadata."""
        mock_container.read_file.return_value = "data:audio/mpeg;base64,SUQzBAAAAAAAI1RTU0..."
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/audio.mp3")

        assert result.success is True
        assert result.metadata["is_binary"] is True
        assert result.metadata["type"] == "binary"
        assert result.metadata["mime_type"] == "audio/mpeg"
        # Should NOT store binary data
        assert "data" not in result.metadata

    @pytest.mark.asyncio
    async def test_read_pdf_file(self, mock_container):
        """Test reading a PDF file - should not store binary data in metadata."""
        mock_container.read_file.return_value = "data:application/pdf;base64,JVBERi0xLjQK..."
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/document.pdf")

        assert result.success is True
        assert result.metadata["is_binary"] is True
        assert result.metadata["type"] == "binary"
        assert result.metadata["mime_type"] == "application/pdf"
        # Should NOT store binary data
        assert "data" not in result.metadata

    @pytest.mark.asyncio
    async def test_read_generic_binary_file(self, mock_container):
        """Test reading a generic binary file - should not store binary data."""
        mock_container.read_file.return_value = "data:application/octet-stream;base64,f0VMRgI..."
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/binary.bin")

        assert result.success is True
        assert result.metadata["is_binary"] is True
        assert result.metadata["type"] == "binary"
        # Should NOT store binary data
        assert "data" not in result.metadata

    @pytest.mark.asyncio
    async def test_image_vs_other_binary_handling(self, mock_container):
        """Test that images store data but other binaries don't."""
        tool = FileReadTool(mock_container)

        # Image should store data in metadata
        mock_container.read_file.return_value = "data:image/png;base64,iVBORw0KGgo..."
        image_result = await tool.execute(path="/workspace/out/image.png")
        assert image_result.metadata["type"] == "image"
        assert "image_data" in image_result.metadata

        # Video should NOT store data in metadata
        mock_container.read_file.return_value = "data:video/mp4;base64,AAAAIGZ0eXBpc29t..."
        video_result = await tool.execute(path="/workspace/out/video.mp4")
        assert video_result.metadata["type"] == "binary"
        assert "data" not in video_result.metadata
        assert "image_data" not in video_result.metadata

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, mock_container):
        """Test reading a non-existent file."""
        mock_container.read_file.return_value = None
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/missing.py")

        assert result.success is False
        assert "not found" in result.error.lower() or "cannot be read" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_invalid_path(self, mock_container):
        """Test reading with invalid path."""
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/etc/passwd")

        assert result.success is False
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_file_exception(self, mock_container):
        """Test handling file read exceptions."""
        mock_container.read_file.side_effect = Exception("Read error")
        tool = FileReadTool(mock_container)

        result = await tool.execute(path="/workspace/out/test.py")

        assert result.success is False
        assert "Failed to read" in result.error

    @pytest.mark.asyncio
    async def test_validate_path_required(self, mock_container):
        """Test path validation through input schema."""
        tool = FileReadTool(mock_container)

        # Invalid path (not starting with /workspace/)
        result = await tool.validate_and_execute(path="/other/path.py")

        assert result.success is False
        assert result.is_validation_error is True


@pytest.mark.unit
class TestFileWriteTool:
    """Test cases for FileWriteTool."""

    @pytest.fixture
    def mock_container(self, mock_docker_container):
        """Create a mock SandboxContainer for testing."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )
        container.write_file = AsyncMock(return_value=True)
        return container

    def test_tool_properties(self, mock_container):
        """Test FileWriteTool properties."""
        tool = FileWriteTool(mock_container)

        assert tool.name == "file_write"
        assert "write" in tool.description.lower() or "create" in tool.description.lower()
        assert len(tool.parameters) == 2

        param_names = [p.name for p in tool.parameters]
        assert "filename" in param_names
        assert "content" in param_names

    @pytest.mark.asyncio
    async def test_write_file_success(self, mock_container):
        """Test writing a file successfully."""
        tool = FileWriteTool(mock_container)

        result = await tool.execute(filename="script.py", content="print('Hello')")

        assert result.success is True
        assert "script.py" in result.output
        assert result.metadata["filename"] == "script.py"
        assert result.metadata["output_path"] == "/workspace/out/script.py"
        mock_container.write_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_file_with_size(self, mock_container):
        """Test that output includes file size."""
        tool = FileWriteTool(mock_container)
        content = "x" * 100

        result = await tool.execute(filename="test.txt", content=content)

        assert result.success is True
        assert result.metadata["size"] == 100

    @pytest.mark.asyncio
    async def test_write_file_failure(self, mock_container):
        """Test handling write failure."""
        mock_container.write_file.return_value = False
        tool = FileWriteTool(mock_container)

        result = await tool.execute(filename="test.py", content="content")

        assert result.success is False
        assert "Failed to write" in result.error

    @pytest.mark.asyncio
    async def test_write_invalid_filename_with_path(self, mock_container):
        """Test rejecting filename with path separators."""
        tool = FileWriteTool(mock_container)

        result = await tool.execute(filename="subdir/script.py", content="content")

        assert result.success is False
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_filename_with_leading_dot(self, mock_container):
        """Test rejecting filename with leading dot."""
        tool = FileWriteTool(mock_container)

        result = await tool.execute(filename=".hidden_file", content="content")

        assert result.success is False
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_exception_handling(self, mock_container):
        """Test handling write exceptions."""
        mock_container.write_file.side_effect = Exception("Write error")
        tool = FileWriteTool(mock_container)

        result = await tool.execute(filename="test.py", content="content")

        assert result.success is False
        assert "Failed to write" in result.error

    @pytest.mark.asyncio
    async def test_validate_filename_schema(self, mock_container):
        """Test filename validation through input schema."""
        tool = FileWriteTool(mock_container)

        # Filename with path separator should fail validation
        result = await tool.validate_and_execute(filename="path/to/file.py", content="content")

        assert result.success is False
        assert result.is_validation_error is True
