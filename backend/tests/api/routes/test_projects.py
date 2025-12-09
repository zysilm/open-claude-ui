"""Tests for Projects API routes."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.api.routes.projects import router
from app.models.database import Project, AgentConfiguration


@pytest.fixture
def app(db_session):
    """Create FastAPI app with projects router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def get_test_db():
        yield db_session

    from app.core.storage.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.mark.api
class TestProjectsAPI:
    """Test cases for Projects API."""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, app, db_session):
        """Test listing projects when empty."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_projects(self, app, db_session, sample_project):
        """Test listing projects."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(p["id"] == sample_project.id for p in data["projects"])

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, app, db_session):
        """Test project listing with pagination."""
        # Create multiple projects
        for i in range(5):
            project = Project(name=f"Project {i}")
            db_session.add(project)
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_create_project(self, app, db_session):
        """Test creating a new project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/projects", json={"name": "New Project", "description": "Test description"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["description"] == "Test description"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_project_with_agent_config(self, app, db_session):
        """Test that creating project also creates agent config."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/projects", json={"name": "Project with Config"})

        assert response.status_code == 201
        project_id = response.json()["id"]

        # Check that agent config was created
        query = select(AgentConfiguration).where(AgentConfiguration.project_id == project_id)
        result = await db_session.execute(query)
        config = result.scalar_one_or_none()

        assert config is not None
        assert config.project_id == project_id

    @pytest.mark.asyncio
    async def test_get_project(self, app, db_session, sample_project):
        """Test getting a project by ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/projects/{sample_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_project.id
        assert data["name"] == sample_project.name

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, app, db_session):
        """Test getting a non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project(self, app, db_session, sample_project):
        """Test updating a project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/projects/{sample_project.id}",
                json={"name": "Updated Name", "description": "Updated description"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_project_partial(self, app, db_session, sample_project):
        """Test partial project update."""
        original_description = sample_project.description

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/projects/{sample_project.id}", json={"name": "Only Name Updated"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Only Name Updated"
        # Description should remain unchanged
        assert data["description"] == original_description

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, app, db_session):
        """Test updating a non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/projects/nonexistent-id", json={"name": "New Name"}
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project(self, app, db_session, sample_project):
        """Test deleting a project."""
        project_id = sample_project.id

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/api/v1/projects/{project_id}")

        assert response.status_code == 204

        # Verify deletion
        query = select(Project).where(Project.id == project_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, app, db_session):
        """Test deleting a non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/projects/nonexistent-id")

        assert response.status_code == 404


@pytest.mark.api
class TestAgentConfigAPI:
    """Test cases for Agent Configuration API."""

    @pytest.mark.asyncio
    async def test_get_agent_config(self, app, db_session, sample_project, sample_agent_config):
        """Test getting agent configuration."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/projects/{sample_project.id}/agent-config")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == sample_project.id
        assert data["llm_provider"] == sample_agent_config.llm_provider

    @pytest.mark.asyncio
    async def test_get_agent_config_not_found(self, app, db_session):
        """Test getting config for non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects/nonexistent/agent-config")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent_config(self, app, db_session, sample_project, sample_agent_config):
        """Test updating agent configuration."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/projects/{sample_project.id}/agent-config",
                json={"llm_model": "gpt-4o", "llm_config": {"temperature": 0.5}},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["llm_model"] == "gpt-4o"
        assert data["llm_config"]["temperature"] == 0.5


@pytest.mark.api
class TestChatSessionAPI:
    """Test cases for Chat Session API."""

    @pytest.mark.asyncio
    async def test_create_chat_session(self, app, db_session, sample_project):
        """Test creating a chat session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/projects/{sample_project.id}/chat-sessions",
                json={"name": "New Chat Session"},
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
                "/api/v1/projects/nonexistent/chat-sessions", json={"name": "Session"}
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_chat_sessions(self, app, db_session, sample_project, sample_chat_session):
        """Test listing chat sessions for a project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/projects/{sample_project.id}/chat-sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(s["id"] == sample_chat_session.id for s in data["chat_sessions"])

    @pytest.mark.asyncio
    async def test_list_chat_sessions_project_not_found(self, app, db_session):
        """Test listing sessions for non-existent project."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects/nonexistent/chat-sessions")

        assert response.status_code == 404
