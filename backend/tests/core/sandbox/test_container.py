"""Tests for SandboxContainer."""

import pytest
from unittest.mock import MagicMock

from app.core.sandbox.container import SandboxContainer


@pytest.mark.unit
class TestSandboxContainer:
    """Test cases for SandboxContainer."""

    def test_init(self, mock_docker_container):
        """Test container initialization."""
        container = SandboxContainer(
            container=mock_docker_container, workspace_path="/tmp/test_workspace"
        )

        assert container.container == mock_docker_container
        assert container.workspace_path == "/tmp/test_workspace"
        assert container.container_id == mock_docker_container.id

    def test_is_running_true(self, mock_docker_container):
        """Test is_running returns True when container is running."""
        mock_docker_container.status = "running"
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        assert container.is_running is True
        mock_docker_container.reload.assert_called_once()

    def test_is_running_false(self, mock_docker_container):
        """Test is_running returns False when container is not running."""
        mock_docker_container.status = "exited"
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        assert container.is_running is False

    def test_is_running_exception(self, mock_docker_container):
        """Test is_running returns False when exception occurs."""
        mock_docker_container.reload.side_effect = Exception("Container not found")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        assert container.is_running is False

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_docker_container):
        """Test executing command successfully."""
        mock_docker_container.exec_run.return_value = MagicMock(
            exit_code=0, output=(b"output", b"")
        )
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        exit_code, stdout, stderr = await container.execute("ls -la")

        assert exit_code == 0
        assert stdout == "output"
        assert stderr == ""
        mock_docker_container.exec_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_stderr(self, mock_docker_container):
        """Test executing command with stderr output."""
        mock_docker_container.exec_run.return_value = MagicMock(
            exit_code=1, output=(b"", b"error message")
        )
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        exit_code, stdout, stderr = await container.execute("invalid_command")

        assert exit_code == 1
        assert stdout == ""
        assert stderr == "error message"

    @pytest.mark.asyncio
    async def test_execute_with_workdir(self, mock_docker_container):
        """Test executing command with custom workdir."""
        mock_docker_container.exec_run.return_value = MagicMock(
            exit_code=0, output=(b"success", b"")
        )
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        await container.execute("python script.py", workdir="/workspace/out")

        mock_docker_container.exec_run.assert_called_once()
        call_args = mock_docker_container.exec_run.call_args
        assert call_args.kwargs["workdir"] == "/workspace/out"

    @pytest.mark.asyncio
    async def test_execute_exception(self, mock_docker_container):
        """Test execute handles exceptions."""
        mock_docker_container.exec_run.side_effect = Exception("Container error")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        exit_code, stdout, stderr = await container.execute("ls")

        assert exit_code == 1
        assert stdout == ""
        assert "Execution error" in stderr

    @pytest.mark.asyncio
    async def test_write_file(self, mock_docker_container):
        """Test writing file to container."""
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        success = await container.write_file("/workspace/out/test.py", "print('Hello')")

        assert success is True
        mock_docker_container.put_archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_file_failure(self, mock_docker_container):
        """Test write_file handles failures."""
        mock_docker_container.put_archive.side_effect = Exception("Write error")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        success = await container.write_file("/workspace/out/test.py", "content")

        assert success is False

    @pytest.mark.asyncio
    async def test_read_file_text(self, mock_docker_container):
        """Test reading text file from container."""
        import io
        import tarfile

        # Create a mock tar archive with text content
        tar_bytes = io.BytesIO()
        tar = tarfile.open(fileobj=tar_bytes, mode="w")
        content = b"print('Hello, World!')"
        tarinfo = tarfile.TarInfo(name="test.py")
        tarinfo.size = len(content)
        tar.addfile(tarinfo, io.BytesIO(content))
        tar.close()
        tar_bytes.seek(0)

        def get_archive_mock(path):
            tar_bytes.seek(0)
            return iter([tar_bytes.read()]), {"name": "test.py"}

        mock_docker_container.get_archive = get_archive_mock
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        result = await container.read_file("/workspace/out/test.py")

        assert result == "print('Hello, World!')"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, mock_docker_container):
        """Test read_file raises exception for missing file."""
        mock_docker_container.get_archive.side_effect = Exception("File not found")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        with pytest.raises(Exception) as exc_info:
            await container.read_file("/workspace/out/missing.py")

        assert "Failed to read file" in str(exc_info.value)

    def test_stop(self, mock_docker_container):
        """Test stopping container."""
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        container.stop()

        mock_docker_container.stop.assert_called_once_with(timeout=5)

    def test_stop_exception(self, mock_docker_container):
        """Test stop handles exceptions gracefully."""
        mock_docker_container.stop.side_effect = Exception("Stop error")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        # Should not raise
        container.stop()

    def test_remove(self, mock_docker_container):
        """Test removing container."""
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        container.remove()

        mock_docker_container.remove.assert_called_once_with(force=True)

    def test_remove_exception(self, mock_docker_container):
        """Test remove handles exceptions gracefully."""
        mock_docker_container.remove.side_effect = Exception("Remove error")
        container = SandboxContainer(mock_docker_container, "/tmp/ws")

        # Should not raise
        container.remove()
