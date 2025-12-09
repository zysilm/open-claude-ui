"""
Unit tests for projects API routes.
Tests template listing, template application, and chat session endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.storage.database import Base, get_db


@pytest.fixture
async def test_app():
    """Create a test FastAPI app with database."""
    from fastapi import FastAPI
    from app.api.routes import projects

    # Create in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI()
    app.include_router(projects.router, prefix="/api/v1")

    async def get_test_db():
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db

    yield app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(test_app):
    """Create async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
class TestProjectTemplateEndpoints:
    """Test template-related project endpoints."""

    async def test_list_agent_templates(self, client: AsyncClient):
        """Test listing all agent templates."""
        response = await client.get("/api/v1/projects/templates/list")
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        # Should have at least the default template
        assert len(templates) >= 1

        # Check template structure
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "agent_type" in template
            assert "enabled_tools" in template

    async def test_get_agent_template_default(self, client: AsyncClient):
        """Test getting the default agent template."""
        response = await client.get("/api/v1/projects/templates/default")
        assert response.status_code == 200
        template = response.json()
        assert template["id"] == "default"
        assert "agent_type" in template
        assert "llm_provider" in template
        assert "enabled_tools" in template

    async def test_get_agent_template_not_found(self, client: AsyncClient):
        """Test getting a non-existent template."""
        response = await client.get("/api/v1/projects/templates/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_apply_template_to_project(self, client: AsyncClient):
        """Test applying a template to a project's agent configuration."""
        # Create project first
        create_resp = await client.post("/api/v1/projects", json={"name": "Template Test Project"})
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # Apply default template
        response = await client.post(
            f"/api/v1/projects/{project_id}/agent-config/apply-template/default"
        )
        assert response.status_code == 200
        config = response.json()
        assert config["agent_type"] == "code_agent"

    async def test_apply_template_project_not_found(self, client: AsyncClient):
        """Test applying template to non-existent project."""
        response = await client.post(
            "/api/v1/projects/nonexistent/agent-config/apply-template/default"
        )
        assert response.status_code == 404

    async def test_apply_template_not_found(self, client: AsyncClient):
        """Test applying non-existent template."""
        # Create project first
        create_resp = await client.post(
            "/api/v1/projects", json={"name": "Template Test Project 2"}
        )
        project_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/projects/{project_id}/agent-config/apply-template/nonexistent"
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestProjectChatSessionEndpoints:
    """Test chat session endpoints nested under projects."""

    async def test_create_chat_session(self, client: AsyncClient):
        """Test creating a chat session for a project."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "Session Test Project"})
        project_id = project_resp.json()["id"]

        # Create session
        response = await client.post(
            f"/api/v1/projects/{project_id}/chat-sessions", json={"name": "Test Session"}
        )
        assert response.status_code == 201
        session = response.json()
        assert session["name"] == "Test Session"
        assert session["project_id"] == project_id
        assert "id" in session

    async def test_create_chat_session_project_not_found(self, client: AsyncClient):
        """Test creating session for non-existent project."""
        response = await client.post(
            "/api/v1/projects/nonexistent/chat-sessions", json={"name": "Test Session"}
        )
        assert response.status_code == 404

    async def test_list_project_chat_sessions(self, client: AsyncClient):
        """Test listing chat sessions for a project."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "List Sessions Project"})
        project_id = project_resp.json()["id"]

        # Create multiple sessions
        for i in range(3):
            await client.post(
                f"/api/v1/projects/{project_id}/chat-sessions", json={"name": f"Session {i}"}
            )

        # List sessions
        response = await client.get(f"/api/v1/projects/{project_id}/chat-sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["chat_sessions"]) == 3

    async def test_list_chat_sessions_project_not_found(self, client: AsyncClient):
        """Test listing sessions for non-existent project."""
        response = await client.get("/api/v1/projects/nonexistent/chat-sessions")
        assert response.status_code == 404

    async def test_list_chat_sessions_pagination(self, client: AsyncClient):
        """Test pagination for chat sessions."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "Pagination Project"})
        project_id = project_resp.json()["id"]

        # Create 5 sessions
        for i in range(5):
            await client.post(
                f"/api/v1/projects/{project_id}/chat-sessions", json={"name": f"Session {i}"}
            )

        # Test pagination
        response = await client.get(f"/api/v1/projects/{project_id}/chat-sessions?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["chat_sessions"]) == 2
        assert data["total"] == 5


@pytest.mark.asyncio
class TestProjectAgentConfigEndpoints:
    """Test agent configuration endpoints."""

    async def test_get_agent_config_not_found(self, client: AsyncClient):
        """Test getting config for project without config."""
        response = await client.get("/api/v1/projects/nonexistent/agent-config")
        assert response.status_code == 404

    async def test_update_agent_config_not_found(self, client: AsyncClient):
        """Test updating config for non-existent project."""
        response = await client.put(
            "/api/v1/projects/nonexistent/agent-config", json={"llm_model": "gpt-4o"}
        )
        assert response.status_code == 404

    async def test_update_agent_config_partial(self, client: AsyncClient):
        """Test partial update of agent configuration."""
        # Create project (auto-creates config)
        project_resp = await client.post("/api/v1/projects", json={"name": "Config Update Project"})
        project_id = project_resp.json()["id"]

        # Partial update - only model
        response = await client.put(
            f"/api/v1/projects/{project_id}/agent-config", json={"llm_model": "gpt-4o"}
        )
        assert response.status_code == 200
        config = response.json()
        assert config["llm_model"] == "gpt-4o"
        # Other fields should remain unchanged
        assert config["llm_provider"] == "openai"

    async def test_update_agent_config_multiple_fields(self, client: AsyncClient):
        """Test updating multiple config fields."""
        # Create project
        project_resp = await client.post("/api/v1/projects", json={"name": "Multi Update Project"})
        project_id = project_resp.json()["id"]

        # Update multiple fields
        response = await client.put(
            f"/api/v1/projects/{project_id}/agent-config",
            json={
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "enabled_tools": ["bash", "file_read"],
                "llm_config": {"temperature": 0.5, "max_tokens": 8000},
            },
        )
        assert response.status_code == 200
        config = response.json()
        assert config["llm_provider"] == "anthropic"
        assert config["llm_model"] == "claude-3-sonnet"
        assert config["enabled_tools"] == ["bash", "file_read"]
        assert config["llm_config"]["temperature"] == 0.5
