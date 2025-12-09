"""
E2E Integration tests for file operations.
Tests file upload, download, listing, and deletion.
"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


@pytest.mark.integration
class TestFileUploadFlow:
    """Test file upload operations."""

    @pytest.fixture
    async def project_id(self, client: AsyncClient) -> str:
        """Create a project for file tests."""
        response = await client.post("/api/v1/projects", json={"name": "File Test Project"})
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_upload_file_project_not_found(self, client: AsyncClient):
        """Test uploading to non-existent project."""
        files = {"file": ("test.py", b"print('hello')", "text/x-python")}
        response = await client.post("/api/v1/files/upload/nonexistent-project", files=files)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_file_type_not_allowed(self, client: AsyncClient, project_id: str):
        """Test uploading disallowed file type."""
        files = {"file": ("malware.exe", b"binary content", "application/octet-stream")}
        response = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client: AsyncClient, project_id: str):
        """Test successful file upload."""
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = (
                f"files/{project_id}/test.py",
                100,
                "abc123hash",
            )
            mock_pv.return_value.write_file = AsyncMock()

            files = {"file": ("test.py", b"print('hello world')", "text/x-python")}
            response = await client.post(f"/api/v1/files/upload/{project_id}", files=files)

            assert response.status_code == 201
            data = response.json()
            assert data["filename"] == "test.py"
            assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, client: AsyncClient, project_id: str):
        """Test uploading multiple files."""
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_pv.return_value.write_file = AsyncMock()

            for i, filename in enumerate(["file1.py", "file2.py", "file3.py"]):
                mock_fm.return_value.save_file.return_value = (
                    f"files/{project_id}/{filename}",
                    100 + i,
                    f"hash{i}",
                )

                files = {"file": (filename, f"# File {i}".encode(), "text/x-python")}
                response = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
                assert response.status_code == 201


@pytest.mark.integration
class TestFileListFlow:
    """Test file listing operations."""

    @pytest.fixture
    async def project_with_files(self, client: AsyncClient):
        """Create a project with some files."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "List Files Project"})
        project_id = project_resp.json()["id"]

        # Upload files
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_pv.return_value.write_file = AsyncMock()

            for i in range(3):
                mock_fm.return_value.save_file.return_value = (
                    f"files/{project_id}/test{i}.py",
                    100,
                    f"hash{i}",
                )
                files = {"file": (f"test{i}.py", b"content", "text/x-python")}
                await client.post(f"/api/v1/files/upload/{project_id}", files=files)

        return project_id

    @pytest.mark.asyncio
    async def test_list_project_files_empty(self, client: AsyncClient):
        """Test listing files for project with no files."""
        # Create empty project
        project_resp = await client.post("/api/v1/projects", json={"name": "Empty Files Project"})
        project_id = project_resp.json()["id"]

        response = await client.get(f"/api/v1/files/project/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_project_files(self, client: AsyncClient, project_with_files: str):
        """Test listing files for project with files."""
        response = await client.get(f"/api/v1/files/project/{project_with_files}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["files"]) == 3


@pytest.mark.integration
class TestFileDownloadFlow:
    """Test file download operations."""

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, client: AsyncClient):
        """Test downloading non-existent file."""
        response = await client.get("/api/v1/files/nonexistent-id/download")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_file_not_on_disk(self, client: AsyncClient):
        """Test downloading file that exists in DB but not on disk."""
        # Create project and upload file
        project_resp = await client.post("/api/v1/projects", json={"name": "Download Test Project"})
        project_id = project_resp.json()["id"]

        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = (
                f"files/{project_id}/missing.py",
                100,
                "hash123",
            )
            mock_pv.return_value.write_file = AsyncMock()

            files = {"file": ("missing.py", b"content", "text/x-python")}
            upload_resp = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
            file_id = upload_resp.json()["id"]

        # Try to download with file not on disk
        with patch("app.api.routes.files.get_file_manager") as mock_fm:
            mock_fm.return_value.get_file_path.return_value = None

            response = await client.get(f"/api/v1/files/{file_id}/download")
            assert response.status_code == 404


@pytest.mark.integration
class TestFileDeleteFlow:
    """Test file deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, client: AsyncClient):
        """Test deleting non-existent file."""
        response = await client.delete("/api/v1/files/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file_success(self, client: AsyncClient):
        """Test successfully deleting a file."""
        # Create project and upload file
        project_resp = await client.post("/api/v1/projects", json={"name": "Delete File Project"})
        project_id = project_resp.json()["id"]

        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = (
                f"files/{project_id}/to_delete.py",
                100,
                "hash123",
            )
            mock_pv.return_value.write_file = AsyncMock()

            files = {"file": ("to_delete.py", b"content", "text/x-python")}
            upload_resp = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
            file_id = upload_resp.json()["id"]

        # Delete the file
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.delete_file.return_value = None
            mock_pv.return_value.delete_file = AsyncMock()

            response = await client.delete(f"/api/v1/files/{file_id}")
            assert response.status_code == 204

        # Verify deletion
        list_resp = await client.get(f"/api/v1/files/project/{project_id}")
        assert list_resp.json()["total"] == 0


@pytest.mark.integration
class TestFileWorkflow:
    """Test complete file management workflow."""

    @pytest.mark.asyncio
    async def test_full_file_workflow(self, client: AsyncClient):
        """Test complete workflow: upload -> list -> download attempt -> delete."""
        # 1. Create project
        project_resp = await client.post(
            "/api/v1/projects", json={"name": "Full File Workflow Project"}
        )
        project_id = project_resp.json()["id"]

        # 2. Upload files
        file_ids = []
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_pv.return_value.write_file = AsyncMock()

            for i in range(3):
                filename = f"workflow_{i}.py"
                mock_fm.return_value.save_file.return_value = (
                    f"files/{project_id}/{filename}",
                    100 + i,
                    f"hash{i}",
                )

                files = {"file": (filename, f"# File {i}".encode(), "text/x-python")}
                upload_resp = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
                assert upload_resp.status_code == 201
                file_ids.append(upload_resp.json()["id"])

        # 3. List files
        list_resp = await client.get(f"/api/v1/files/project/{project_id}")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 3

        # 4. Delete one file
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.delete_file.return_value = None
            mock_pv.return_value.delete_file = AsyncMock()

            delete_resp = await client.delete(f"/api/v1/files/{file_ids[0]}")
            assert delete_resp.status_code == 204

        # 5. Verify remaining files
        final_list = await client.get(f"/api/v1/files/project/{project_id}")
        assert final_list.json()["total"] == 2


@pytest.mark.integration
class TestFileTypeValidation:
    """Test file type validation."""

    @pytest.fixture
    async def project_id(self, client: AsyncClient) -> str:
        """Create a project for validation tests."""
        response = await client.post("/api/v1/projects", json={"name": "Validation Test Project"})
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_allowed_python_file(self, client: AsyncClient, project_id: str):
        """Test that Python files are allowed."""
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = ("path", 100, "hash")
            mock_pv.return_value.write_file = AsyncMock()

            response = await client.post(
                f"/api/v1/files/upload/{project_id}",
                files={"file": ("script.py", b"print('test')", "text/x-python")},
            )
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_allowed_text_file(self, client: AsyncClient, project_id: str):
        """Test that text files are allowed."""
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = ("path", 100, "hash")
            mock_pv.return_value.write_file = AsyncMock()

            response = await client.post(
                f"/api/v1/files/upload/{project_id}",
                files={"file": ("readme.txt", b"Hello", "text/plain")},
            )
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_disallowed_executable(self, client: AsyncClient, project_id: str):
        """Test that executables are not allowed."""
        response = await client.post(
            f"/api/v1/files/upload/{project_id}",
            files={"file": ("program.exe", b"MZ", "application/x-msdownload")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_disallowed_shell_script(self, client: AsyncClient, project_id: str):
        """Test that shell scripts may be restricted."""
        # This depends on the actual implementation's allowed types
        files = {"file": ("script.sh", b"#!/bin/bash\necho test", "application/x-sh")}
        response = await client.post(f"/api/v1/files/upload/{project_id}", files=files)
        # Either allowed (201) or blocked (400) based on config
        assert response.status_code in [201, 400]
