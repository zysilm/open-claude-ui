"""Tests for workspace storage backends."""

import pytest
from pathlib import Path
import tempfile
import shutil

from app.core.storage.local_storage import LocalStorage
from app.core.storage.workspace_storage import FileInfo


class TestLocalStorage:
    """Test local filesystem storage."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def storage(self, temp_workspace):
        """Create LocalStorage instance."""
        return LocalStorage(workspace_base=temp_workspace)

    @pytest.mark.asyncio
    async def test_create_workspace(self, storage):
        """Test creating a workspace."""
        session_id = "test-session"

        await storage.create_workspace(session_id)

        # Verify subdirectories exist
        workspace_path = storage._get_workspace_path(session_id)
        assert workspace_path.exists()
        assert (workspace_path / "project_files").exists()
        assert (workspace_path / "agent_workspace").exists()
        assert (workspace_path / "out").exists()

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, storage):
        """Test writing and reading files."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # Write file
        content = b"Hello, World!"
        success = await storage.write_file(session_id, "/workspace/out/test.txt", content)
        assert success

        # Read file
        read_content = await storage.read_file(session_id, "/workspace/out/test.txt")
        assert read_content == content

    @pytest.mark.asyncio
    async def test_file_not_found(self, storage):
        """Test reading non-existent file."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        with pytest.raises(FileNotFoundError):
            await storage.read_file(session_id, "/workspace/nonexistent.txt")

    @pytest.mark.asyncio
    async def test_file_exists(self, storage):
        """Test checking file existence."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # File doesn't exist yet
        exists = await storage.file_exists(session_id, "/workspace/out/test.txt")
        assert not exists

        # Create file
        await storage.write_file(session_id, "/workspace/out/test.txt", b"content")

        # File exists now
        exists = await storage.file_exists(session_id, "/workspace/out/test.txt")
        assert exists

    @pytest.mark.asyncio
    async def test_delete_file(self, storage):
        """Test deleting a file."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # Create file
        await storage.write_file(session_id, "/workspace/out/test.txt", b"content")
        assert await storage.file_exists(session_id, "/workspace/out/test.txt")

        # Delete file
        success = await storage.delete_file(session_id, "/workspace/out/test.txt")
        assert success

        # File should be gone
        exists = await storage.file_exists(session_id, "/workspace/out/test.txt")
        assert not exists

    @pytest.mark.asyncio
    async def test_list_files(self, storage):
        """Test listing files."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # Create some files
        await storage.write_file(session_id, "/workspace/out/file1.txt", b"content1")
        await storage.write_file(session_id, "/workspace/out/file2.txt", b"content2")

        # List files
        files = await storage.list_files(session_id, "/workspace/out")

        assert len(files) == 2
        file_names = [Path(f.path).name for f in files]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names

    @pytest.mark.asyncio
    async def test_delete_workspace(self, storage):
        """Test deleting entire workspace."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # Create some files
        await storage.write_file(session_id, "/workspace/out/test.txt", b"content")

        # Delete workspace
        await storage.delete_workspace(session_id)

        # Workspace should be gone
        workspace_path = storage._get_workspace_path(session_id)
        assert not workspace_path.exists()

    @pytest.mark.asyncio
    async def test_copy_to_workspace(self, storage, temp_workspace):
        """Test copying files from host to workspace."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        # Create a source file
        source_file = Path(temp_workspace) / "source.txt"
        source_file.write_text("Source content")

        # Copy to workspace
        await storage.copy_to_workspace(
            session_id,
            source_file,
            "/workspace/project_files/source.txt"
        )

        # Verify file was copied
        content = await storage.read_file(session_id, "/workspace/project_files/source.txt")
        assert content == b"Source content"

    @pytest.mark.asyncio
    async def test_get_volume_config(self, storage):
        """Test getting Docker volume configuration."""
        session_id = "test-session"
        await storage.create_workspace(session_id)

        config = storage.get_volume_config(session_id)

        assert isinstance(config, dict)
        assert len(config) == 1  # Should have one volume mapping

        # Check bind mount configuration
        for host_path, mount_config in config.items():
            assert mount_config["bind"] == "/workspace"
            assert mount_config["mode"] == "rw"


# VolumeStorage and S3Storage tests would require Docker/S3 setup
# Mark them as integration tests

@pytest.mark.integration
@pytest.mark.container
class TestVolumeStorage:
    """Integration tests for Docker volume storage (requires Docker)."""

    @pytest.mark.asyncio
    async def test_volume_creation(self, skip_if_no_docker):
        """Test creating Docker volume."""
        import docker
        from app.core.storage.volume_storage import VolumeStorage

        client = docker.from_env()
        storage = VolumeStorage(docker_client=client)
        session_id = "test-volume-session"

        try:
            await storage.create_workspace(session_id)

            # Verify volume exists
            volume_name = storage._get_volume_name(session_id)
            volume = client.volumes.get(volume_name)
            assert volume is not None

        finally:
            # Cleanup
            await storage.delete_workspace(session_id)

    @pytest.mark.asyncio
    async def test_volume_file_operations(self, skip_if_no_docker):
        """Test file operations with Docker volumes."""
        import docker
        from app.core.storage.volume_storage import VolumeStorage

        client = docker.from_env()
        storage = VolumeStorage(docker_client=client)
        session_id = "test-volume-files"

        try:
            await storage.create_workspace(session_id)

            # Write file
            content = b"Test content in volume"
            success = await storage.write_file(session_id, "/workspace/out/test.txt", content)
            assert success

            # Read file
            read_content = await storage.read_file(session_id, "/workspace/out/test.txt")
            assert read_content == content

        finally:
            await storage.delete_workspace(session_id)
