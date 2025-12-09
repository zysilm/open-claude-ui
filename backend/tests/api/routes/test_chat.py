"""Tests for Chat API routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.api.routes.chat import router, WorkspaceFile, WorkspaceFilesResponse
from app.models.database import ChatSession, Project, ContentBlock
from app.models.database.content_block import ContentBlockType, ContentBlockAuthor


@pytest.fixture
def app(db_session):
    """Create FastAPI app with chat router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def get_test_db():
        yield db_session

    from app.core.storage.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.mark.api
class TestChatSessionAPI:
    """Test cases for Chat Session API."""

    @pytest.mark.asyncio
    async def test_list_chat_sessions_empty(self, app, db_session):
        """Test listing chat sessions when empty."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chats")

        assert response.status_code == 200
        data = response.json()
        assert data["chat_sessions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_chat_sessions(self, app, db_session, sample_chat_session):
        """Test listing chat sessions."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(s["id"] == sample_chat_session.id for s in data["chat_sessions"])

    @pytest.mark.asyncio
    async def test_list_chat_sessions_filter_by_project(
        self, app, db_session, sample_project, sample_chat_session
    ):
        """Test filtering chat sessions by project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/chats?project_id={sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(s["project_id"] == sample_project.id for s in data["chat_sessions"])

    @pytest.mark.asyncio
    async def test_create_chat_session(self, app, db_session, sample_project):
        """Test creating a chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/chats?project_id={sample_project.id}", json={"name": "New Chat Session"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Chat Session"
        assert data["project_id"] == sample_project.id

    @pytest.mark.asyncio
    async def test_create_chat_session_project_not_found(self, app, db_session):
        """Test creating chat session for non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chats?project_id=nonexistent", json={"name": "Session"}
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_chat_session(self, app, db_session, sample_chat_session):
        """Test getting a chat session by ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/chats/{sample_chat_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_chat_session.id
        assert data["name"] == sample_chat_session.name

    @pytest.mark.asyncio
    async def test_get_chat_session_not_found(self, app, db_session):
        """Test getting non-existent chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chats/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_chat_session(self, app, db_session, sample_chat_session):
        """Test updating a chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/chats/{sample_chat_session.id}", json={"name": "Updated Name"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_chat_session_not_found(self, app, db_session):
        """Test updating non-existent chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/v1/chats/nonexistent-id", json={"name": "New Name"})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chat_session(self, app, db_session, sample_chat_session):
        """Test deleting a chat session."""
        session_id = sample_chat_session.id

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/api/v1/chats/{session_id}")

        assert response.status_code == 204

        # Verify deletion
        query = select(ChatSession).where(ChatSession.id == session_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_chat_session_not_found(self, app, db_session):
        """Test deleting non-existent chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/chats/nonexistent-id")

        assert response.status_code == 404


@pytest.mark.api
class TestContentBlocksAPI:
    """Test cases for Content Blocks API."""

    @pytest.mark.asyncio
    async def test_list_content_blocks_empty(self, app, db_session, sample_chat_session):
        """Test listing content blocks when empty."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/chats/{sample_chat_session.id}/blocks")

        assert response.status_code == 200
        data = response.json()
        assert data["blocks"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_content_blocks(self, app, db_session, sample_chat_session):
        """Test listing content blocks."""
        # Create some content blocks
        for i in range(3):
            block = ContentBlock(
                chat_session_id=sample_chat_session.id,
                block_type=(
                    ContentBlockType.USER_TEXT if i % 2 == 0 else ContentBlockType.ASSISTANT_TEXT
                ),
                author=ContentBlockAuthor.USER if i % 2 == 0 else ContentBlockAuthor.ASSISTANT,
                content={"text": f"Test content {i}"},
                sequence_number=i,
            )
            db_session.add(block)
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/chats/{sample_chat_session.id}/blocks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["blocks"]) == 3

    @pytest.mark.asyncio
    async def test_list_content_blocks_session_not_found(self, app, db_session):
        """Test listing blocks for non-existent session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chats/nonexistent/blocks")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_content_block(self, app, db_session, sample_chat_session):
        """Test getting a specific content block."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            block_type=ContentBlockType.USER_TEXT,
            author=ContentBlockAuthor.USER,
            content={"text": "Test content"},
            sequence_number=0,
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/chats/{sample_chat_session.id}/blocks/{block.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == block.id
        assert data["content"]["text"] == "Test content"

    @pytest.mark.asyncio
    async def test_get_content_block_not_found(self, app, db_session, sample_chat_session):
        """Test getting non-existent content block."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/chats/{sample_chat_session.id}/blocks/nonexistent"
            )

        assert response.status_code == 404


@pytest.mark.api
class TestWorkspaceFilesAPI:
    """Test cases for Workspace Files API."""

    @pytest.mark.asyncio
    async def test_list_workspace_files(self, app, db_session, sample_chat_session):
        """Test listing workspace files."""
        # Mock the container manager
        with patch("app.api.routes.chat.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(0, "", ""))
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/chats/{sample_chat_session.id}/workspace/files"
                )

            assert response.status_code == 200
            data = response.json()
            assert "uploaded" in data
            assert "output" in data

    @pytest.mark.asyncio
    async def test_list_workspace_files_session_not_found(self, app, db_session):
        """Test listing files for non-existent session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chats/nonexistent/workspace/files")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workspace_file_content_invalid_path(
        self, app, db_session, sample_chat_session
    ):
        """Test getting file content with invalid path."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/chats/{sample_chat_session.id}/workspace/files/content?path=/etc/passwd"
            )

        assert response.status_code == 400
        assert "workspace" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_workspace_file_content_file_not_found(
        self, app, db_session, sample_chat_session
    ):
        """Test getting content of non-existent file."""
        with patch("app.api.routes.chat.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(1, "", ""))  # File not found
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/chats/{sample_chat_session.id}/workspace/files/content?path=/workspace/out/missing.txt"
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workspace_file_content_success(self, app, db_session, sample_chat_session):
        """Test successfully getting file content."""
        with patch("app.api.routes.chat.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(0, "", ""))  # File exists
            mock_container.read_file = AsyncMock(return_value="file content here")
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/chats/{sample_chat_session.id}/workspace/files/content?path=/workspace/out/test.txt"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["path"] == "/workspace/out/test.txt"
            assert data["content"] == "file content here"
            assert data["is_binary"] is False

    @pytest.mark.asyncio
    async def test_download_workspace_file(self, app, db_session, sample_chat_session):
        """Test downloading a workspace file."""
        with patch("app.api.routes.chat.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(0, "", ""))
            mock_container.read_file = AsyncMock(return_value="file content")
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/chats/{sample_chat_session.id}/workspace/files/download?path=/workspace/out/test.txt"
                )

            assert response.status_code == 200
            assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_all_workspace_files_no_files(
        self, app, db_session, sample_chat_session
    ):
        """Test downloading all files when none exist."""
        with patch("app.api.routes.chat.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(0, "", ""))  # Empty output
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/chats/{sample_chat_session.id}/workspace/download-all?type=output"
                )

            assert response.status_code == 404
            assert "No output files found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_all_invalid_type(self, app, db_session, sample_chat_session):
        """Test downloading with invalid type parameter."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/chats/{sample_chat_session.id}/workspace/download-all?type=invalid"
            )

        assert response.status_code == 400


@pytest.mark.api
class TestUploadToProjectAPI:
    """Test cases for Upload to Project API."""

    @pytest.mark.asyncio
    async def test_upload_to_project_invalid_path(
        self, app, db_session, sample_chat_session, sample_project
    ):
        """Test upload with invalid path."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/chats/{sample_chat_session.id}/workspace/files/upload-to-project",
                json={
                    "path": "/workspace/project_files/test.txt",  # Not from /workspace/out/
                    "project_id": sample_project.id,
                },
            )

        assert response.status_code == 400
        assert "output files" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_to_project_session_not_found(self, app, db_session, sample_project):
        """Test upload with non-existent session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chats/nonexistent/workspace/files/upload-to-project",
                json={
                    "path": "/workspace/out/test.txt",
                    "project_id": sample_project.id,
                },
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_to_project_wrong_project(self, app, db_session, sample_chat_session):
        """Test upload with mismatched project."""
        # Create another project
        other_project = Project(name="Other Project")
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/chats/{sample_chat_session.id}/workspace/files/upload-to-project",
                json={
                    "path": "/workspace/out/test.txt",
                    "project_id": other_project.id,  # Wrong project
                },
            )

        assert response.status_code == 400
        assert "does not belong" in response.json()["detail"].lower()


@pytest.mark.unit
class TestWorkspaceModels:
    """Test cases for Workspace models."""

    def test_workspace_file_model(self):
        """Test WorkspaceFile model."""
        file = WorkspaceFile(
            name="test.py",
            path="/workspace/out/test.py",
            size=1024,
            type="output",
            mime_type="text/x-python",
        )

        assert file.name == "test.py"
        assert file.path == "/workspace/out/test.py"
        assert file.size == 1024
        assert file.type == "output"
        assert file.mime_type == "text/x-python"
        assert file.id is None

    def test_workspace_file_with_id(self):
        """Test WorkspaceFile with ID."""
        file = WorkspaceFile(
            id="file-123",
            name="test.py",
            path="/workspace/project_files/test.py",
            size=512,
            type="uploaded",
        )

        assert file.id == "file-123"

    def test_workspace_files_response(self):
        """Test WorkspaceFilesResponse model."""
        uploaded = [
            WorkspaceFile(
                name="a.py", path="/workspace/project_files/a.py", size=100, type="uploaded"
            ),
        ]
        output = [
            WorkspaceFile(name="b.txt", path="/workspace/out/b.txt", size=200, type="output"),
        ]

        response = WorkspaceFilesResponse(uploaded=uploaded, output=output)

        assert len(response.uploaded) == 1
        assert len(response.output) == 1
        assert response.uploaded[0].name == "a.py"
        assert response.output[0].name == "b.txt"
