"""Tests for LocalStorage backend."""

import pytest

from app.core.storage.local_storage import LocalStorage


@pytest.mark.unit
class TestLocalStorage:
    """Test cases for LocalStorage."""

    @pytest.fixture
    def storage(self, temp_workspace):
        """Create a LocalStorage instance with temp workspace."""
        return LocalStorage(workspace_base=str(temp_workspace))

    @pytest.fixture
    def session_id(self):
        """Provide a test session ID."""
        return "test-session-123"

    def test_init_creates_base_directory(self, temp_workspace):
        """Test that initialization creates base directory."""
        storage = LocalStorage(workspace_base=str(temp_workspace / "new_base"))
        assert storage.workspace_base.exists()

    def test_get_workspace_path(self, storage, session_id):
        """Test getting workspace path for session."""
        path = storage._get_workspace_path(session_id)
        assert path == storage.workspace_base / session_id

    def test_get_host_path(self, storage, session_id):
        """Test converting container path to host path."""
        container_path = "/workspace/out/script.py"
        host_path = storage._get_host_path(session_id, container_path)

        expected = storage.workspace_base / session_id / "out" / "script.py"
        assert host_path == expected

    def test_get_host_path_variations(self, storage, session_id):
        """Test various container path formats."""
        test_cases = [
            ("/workspace/out/file.py", "out/file.py"),
            ("/workspace/project_files/data.csv", "project_files/data.csv"),
            ("/workspace/test.py", "test.py"),
        ]

        for container_path, expected_relative in test_cases:
            host_path = storage._get_host_path(session_id, container_path)
            expected = storage.workspace_base / session_id / expected_relative
            assert host_path == expected

    @pytest.mark.asyncio
    async def test_create_workspace(self, storage, session_id):
        """Test creating a workspace."""
        await storage.create_workspace(session_id)

        workspace = storage._get_workspace_path(session_id)
        assert workspace.exists()
        assert (workspace / "project_files").exists()
        assert (workspace / "out").exists()

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, storage, session_id):
        """Test writing and reading a file."""
        await storage.create_workspace(session_id)

        container_path = "/workspace/out/test.py"
        content = b"print('Hello, World!')"

        # Write
        success = await storage.write_file(session_id, container_path, content)
        assert success is True

        # Read
        read_content = await storage.read_file(session_id, container_path)
        assert read_content == content

    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, storage, session_id):
        """Test that writing creates parent directories."""
        await storage.create_workspace(session_id)

        container_path = "/workspace/out/subdir/nested/file.py"
        content = b"content"

        success = await storage.write_file(session_id, container_path, content)
        assert success is True

        host_path = storage._get_host_path(session_id, container_path)
        assert host_path.exists()

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, storage, session_id):
        """Test reading non-existent file."""
        await storage.create_workspace(session_id)

        with pytest.raises(FileNotFoundError):
            await storage.read_file(session_id, "/workspace/out/missing.py")

    @pytest.mark.asyncio
    async def test_file_exists(self, storage, session_id):
        """Test checking file existence."""
        await storage.create_workspace(session_id)

        container_path = "/workspace/out/exists.py"

        # Before writing
        assert await storage.file_exists(session_id, container_path) is False

        # After writing
        await storage.write_file(session_id, container_path, b"content")
        assert await storage.file_exists(session_id, container_path) is True

    @pytest.mark.asyncio
    async def test_delete_file(self, storage, session_id):
        """Test deleting a file."""
        await storage.create_workspace(session_id)

        container_path = "/workspace/out/to_delete.py"
        await storage.write_file(session_id, container_path, b"content")

        # Delete
        success = await storage.delete_file(session_id, container_path)
        assert success is True
        assert await storage.file_exists(session_id, container_path) is False

    @pytest.mark.asyncio
    async def test_delete_directory(self, storage, session_id):
        """Test deleting a directory."""
        await storage.create_workspace(session_id)

        # Create directory with files
        await storage.write_file(session_id, "/workspace/out/subdir/file1.py", b"1")
        await storage.write_file(session_id, "/workspace/out/subdir/file2.py", b"2")

        # Delete directory
        success = await storage.delete_file(session_id, "/workspace/out/subdir")
        assert success is True

    @pytest.mark.asyncio
    async def test_list_files(self, storage, session_id):
        """Test listing files in a directory."""
        await storage.create_workspace(session_id)

        # Create some files
        await storage.write_file(session_id, "/workspace/out/file1.py", b"1")
        await storage.write_file(session_id, "/workspace/out/file2.py", b"2")
        await storage.write_file(session_id, "/workspace/out/subdir/file3.py", b"3")

        files = await storage.list_files(session_id, "/workspace/out")

        # Should include all files
        paths = [f.path for f in files]
        assert any("file1.py" in p for p in paths)
        assert any("file2.py" in p for p in paths)
        assert any("file3.py" in p for p in paths)

    @pytest.mark.asyncio
    async def test_list_files_empty(self, storage, session_id):
        """Test listing files in empty directory."""
        await storage.create_workspace(session_id)

        files = await storage.list_files(session_id, "/workspace/out")
        assert files == []

    @pytest.mark.asyncio
    async def test_delete_workspace(self, storage, session_id):
        """Test deleting entire workspace."""
        await storage.create_workspace(session_id)
        await storage.write_file(session_id, "/workspace/out/test.py", b"content")

        workspace = storage._get_workspace_path(session_id)
        assert workspace.exists()

        await storage.delete_workspace(session_id)
        assert not workspace.exists()

    @pytest.mark.asyncio
    async def test_copy_to_workspace(self, storage, session_id, temp_file):
        """Test copying files to workspace."""
        await storage.create_workspace(session_id)

        dest_path = "/workspace/project_files/copied_file.py"
        await storage.copy_to_workspace(session_id, temp_file, dest_path)

        assert await storage.file_exists(session_id, dest_path)

    def test_get_volume_config(self, storage, session_id):
        """Test getting Docker volume configuration."""
        config = storage.get_volume_config(session_id)

        workspace_path = storage._get_workspace_path(session_id)
        expected_key = str(workspace_path.absolute())

        assert expected_key in config
        assert config[expected_key]["bind"] == "/workspace"
        assert config[expected_key]["mode"] == "rw"
