"""Tests for Files API routes."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.api.routes.files import router
from app.models.database import File


@pytest.fixture
def app(db_session):
    """Create FastAPI app with files router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def get_test_db():
        yield db_session

    from app.core.storage.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.mark.api
class TestFilesUploadAPI:
    """Test cases for file upload API."""

    @pytest.mark.asyncio
    async def test_upload_file_project_not_found(self, app, db_session):
        """Test uploading to non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/files/upload/nonexistent",
                files={"file": ("test.py", b"print('hello')", "text/x-python")},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_file_type_not_allowed(self, app, db_session, sample_project):
        """Test uploading disallowed file type."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/files/upload/{sample_project.id}",
                files={"file": ("test.exe", b"binary", "application/octet-stream")},
            )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_file_success(self, app, db_session, sample_project):
        """Test successful file upload."""
        # Mock file manager and project storage
        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.save_file.return_value = ("files/test.py", 100, "abc123")
            mock_pv.return_value.write_file = AsyncMock()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/files/upload/{sample_project.id}",
                    files={"file": ("test.py", b"print('hello')", "text/x-python")},
                )

            assert response.status_code == 201
            data = response.json()
            assert data["filename"] == "test.py"
            assert data["project_id"] == sample_project.id


@pytest.mark.api
class TestFilesListAPI:
    """Test cases for listing project files."""

    @pytest.mark.asyncio
    async def test_list_project_files_empty(self, app, db_session, sample_project):
        """Test listing files when none exist."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/files/project/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_project_files(self, app, db_session, sample_project):
        """Test listing project files."""
        # Create some files
        for i in range(3):
            file = File(
                project_id=sample_project.id,
                filename=f"test{i}.py",
                file_path=f"files/{sample_project.id}/test{i}.py",
                file_type="input",
                size=100,
            )
            db_session.add(file)
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/files/project/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["files"]) == 3


@pytest.mark.api
class TestFilesDownloadAPI:
    """Test cases for file download."""

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, app, db_session):
        """Test downloading non-existent file."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/files/nonexistent/download")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_file_not_on_disk(self, app, db_session, sample_project):
        """Test downloading file not on disk."""
        # Create file record but no actual file
        file = File(
            project_id=sample_project.id,
            filename="test.py",
            file_path="files/missing.py",
            file_type="input",
            size=100,
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        with patch("app.api.routes.files.get_file_manager") as mock_fm:
            mock_fm.return_value.get_file_path.return_value = None

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/files/{file.id}/download")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.api
class TestFilesDeleteAPI:
    """Test cases for file deletion."""

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, app, db_session):
        """Test deleting non-existent file."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/files/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file_success(self, app, db_session, sample_project):
        """Test successful file deletion."""
        # Create file record
        file = File(
            project_id=sample_project.id,
            filename="test.py",
            file_path="files/test.py",
            file_type="input",
            size=100,
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        with (
            patch("app.api.routes.files.get_file_manager") as mock_fm,
            patch("app.api.routes.files.get_project_volume_storage") as mock_pv,
        ):

            mock_fm.return_value.delete_file.return_value = None
            mock_pv.return_value.delete_file = AsyncMock()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/files/{file.id}")

            assert response.status_code == 204

            # Verify file was deleted from database
            query = select(File).where(File.id == file.id)
            result = await db_session.execute(query)
            deleted = result.scalar_one_or_none()
            assert deleted is None
