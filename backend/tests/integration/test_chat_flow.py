"""
E2E Integration tests for chat flow.
Tests content blocks, message history, and workspace files.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestChatSessionFlow:
    """Test chat session operations."""

    @pytest.mark.asyncio
    async def test_list_chat_sessions(self, client: AsyncClient):
        """Test listing all chat sessions."""
        response = await client.get("/api/v1/chats")
        assert response.status_code == 200
        data = response.json()
        assert "chat_sessions" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, client: AsyncClient):
        """Test creating and retrieving a chat session."""
        # Create project first
        project_resp = await client.post("/api/v1/projects", json={"name": "Chat Test Project"})
        project_id = project_resp.json()["id"]

        # Create session
        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Test Chat"}
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        # Get session
        get_resp = await client.get(f"/api/v1/chats/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Test Chat"

    @pytest.mark.asyncio
    async def test_filter_sessions_by_project(self, client: AsyncClient):
        """Test filtering chat sessions by project."""
        # Create two projects
        project1_resp = await client.post("/api/v1/projects", json={"name": "Project 1"})
        project1_id = project1_resp.json()["id"]

        project2_resp = await client.post("/api/v1/projects", json={"name": "Project 2"})
        project2_id = project2_resp.json()["id"]

        # Create sessions in each project
        await client.post(
            f"/api/v1/projects/{project1_id}/chat-sessions", json={"name": "P1 Session 1"}
        )
        await client.post(
            f"/api/v1/projects/{project1_id}/chat-sessions", json={"name": "P1 Session 2"}
        )
        await client.post(
            f"/api/v1/projects/{project2_id}/chat-sessions", json={"name": "P2 Session 1"}
        )

        # Filter by project 1
        response = await client.get(f"/api/v1/chats?project_id={project1_id}")
        assert response.status_code == 200
        sessions = response.json()["chat_sessions"]
        assert len(sessions) == 2
        for session in sessions:
            assert session["project_id"] == project1_id


@pytest.mark.integration
class TestContentBlocksFlow:
    """Test content blocks operations."""

    @pytest.fixture
    async def session_with_project(self, client: AsyncClient):
        """Create a project and session for content block tests."""
        project_resp = await client.post("/api/v1/projects", json={"name": "Content Block Project"})
        project_id = project_resp.json()["id"]

        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Content Block Session"}
        )
        session_id = session_resp.json()["id"]

        return {"project_id": project_id, "session_id": session_id}

    @pytest.mark.asyncio
    async def test_list_content_blocks_empty(self, client: AsyncClient, session_with_project):
        """Test listing content blocks for empty session."""
        session_id = session_with_project["session_id"]

        response = await client.get(f"/api/v1/chats/{session_id}/blocks")
        assert response.status_code == 200
        data = response.json()
        assert data["blocks"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_content_block_not_found(self, client: AsyncClient):
        """Test getting non-existent content block."""
        response = await client.get("/api/v1/chat/blocks/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.integration
class TestWorkspaceFilesFlow:
    """Test workspace files operations."""

    @pytest.fixture
    async def session_with_project(self, client: AsyncClient):
        """Create a project and session for workspace tests."""
        project_resp = await client.post(
            "/api/v1/projects", json={"name": "Workspace Test Project"}
        )
        project_id = project_resp.json()["id"]

        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Workspace Test Session"}
        )
        session_id = session_resp.json()["id"]

        return {"project_id": project_id, "session_id": session_id}

    @pytest.mark.asyncio
    async def test_list_workspace_files_empty(self, client: AsyncClient, session_with_project):
        """Test listing workspace files for session with no files."""
        session_id = session_with_project["session_id"]

        response = await client.get(f"/api/v1/chats/{session_id}/workspace/files")
        assert response.status_code == 200
        data = response.json()
        # Response has "uploaded" and "output" keys
        assert data["uploaded"] == []

    @pytest.mark.asyncio
    async def test_list_workspace_files_session_not_found(self, client: AsyncClient):
        """Test listing workspace files for non-existent session."""
        response = await client.get("/api/v1/chats/nonexistent/workspace/files")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workspace_file_invalid_path(self, client: AsyncClient, session_with_project):
        """Test getting workspace file with invalid path."""
        session_id = session_with_project["session_id"]

        # Path traversal attempt - correct endpoint is /workspace/files/content
        response = await client.get(
            f"/api/v1/chats/{session_id}/workspace/files/content",
            params={"path": "../../../etc/passwd"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_download_workspace_no_files(self, client: AsyncClient, session_with_project):
        """Test downloading workspace when empty."""
        session_id = session_with_project["session_id"]

        response = await client.get(
            f"/api/v1/chats/{session_id}/workspace/download-all", params={"type": "output"}
        )
        # Should return 404 or empty zip
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_download_workspace_invalid_type(self, client: AsyncClient, session_with_project):
        """Test downloading workspace with invalid type."""
        session_id = session_with_project["session_id"]

        response = await client.get(
            f"/api/v1/chats/{session_id}/workspace/download-all", params={"type": "invalid_type"}
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestChatHistoryFlow:
    """Test chat history and message flow."""

    @pytest.mark.asyncio
    async def test_session_history_empty(self, client: AsyncClient):
        """Test getting history for a new session."""
        # Create project and session
        project_resp = await client.post("/api/v1/projects", json={"name": "History Test Project"})
        project_id = project_resp.json()["id"]

        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "History Test Session"}
        )
        session_id = session_resp.json()["id"]

        # Get session with blocks
        response = await client.get(f"/api/v1/chats/{session_id}")
        assert response.status_code == 200
        # Session should exist but have no message blocks

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self, client: AsyncClient):
        """Test that sessions are isolated from each other."""
        # Create project
        project_resp = await client.post(
            "/api/v1/projects", json={"name": "Isolation Test Project"}
        )
        project_id = project_resp.json()["id"]

        # Create two sessions
        session1_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Session 1"}
        )
        session1_id = session1_resp.json()["id"]

        session2_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Session 2"}
        )
        session2_id = session2_resp.json()["id"]

        # Verify both exist independently
        s1 = await client.get(f"/api/v1/chats/{session1_id}")
        s2 = await client.get(f"/api/v1/chats/{session2_id}")

        assert s1.status_code == 200
        assert s2.status_code == 200
        assert s1.json()["id"] != s2.json()["id"]
        assert s1.json()["name"] == "Session 1"
        assert s2.json()["name"] == "Session 2"


@pytest.mark.integration
class TestSessionStatusFlow:
    """Test session status management."""

    @pytest.mark.asyncio
    async def test_session_default_status(self, client: AsyncClient):
        """Test that new sessions have active status."""
        # Create project and session
        project_resp = await client.post("/api/v1/projects", json={"name": "Status Test Project"})
        project_id = project_resp.json()["id"]

        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Status Test Session"}
        )
        session_id = session_resp.json()["id"]

        # Get session and check status
        response = await client.get(f"/api/v1/chats/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_session_status(self, client: AsyncClient):
        """Test updating session status."""
        # Create project and session
        project_resp = await client.post("/api/v1/projects", json={"name": "Update Status Project"})
        project_id = project_resp.json()["id"]

        session_resp = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Update Status Session"}
        )
        session_id = session_resp.json()["id"]

        # Update session with new status
        update_resp = await client.put(
            f"/api/v1/chats/{session_id}", json={"name": "Updated Session", "status": "archived"}
        )
        assert update_resp.status_code == 200
        # Check if status is updated (depends on API schema support)


@pytest.mark.integration
class TestChatSessionPagination:
    """Test pagination for chat sessions."""

    @pytest.mark.asyncio
    async def test_sessions_pagination(self, client: AsyncClient):
        """Test chat sessions pagination."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "Pagination Project"})
        project_id = project_resp.json()["id"]

        # Create multiple sessions
        for i in range(10):
            await client.post(
                f"/api/v1/projects/{project_id}/chat-sessions", json={"name": f"Session {i}"}
            )

        # Test pagination
        page1 = await client.get("/api/v1/chats?skip=0&limit=3")
        assert page1.status_code == 200
        data1 = page1.json()
        assert len(data1["chat_sessions"]) <= 3

        page2 = await client.get("/api/v1/chats?skip=3&limit=3")
        assert page2.status_code == 200
        data2 = page2.json()

        # Pages should be different
        if data1["chat_sessions"] and data2["chat_sessions"]:
            page1_ids = {s["id"] for s in data1["chat_sessions"]}
            page2_ids = {s["id"] for s in data2["chat_sessions"]}
            assert page1_ids.isdisjoint(page2_ids)
