"""Tests for Sandbox API routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.routes.sandbox import (
    router,
    ExecuteCommandRequest,
    ExecuteCommandResponse,
    ContainerStatusResponse,
)


@pytest.fixture
def app(db_session):
    """Create FastAPI app with sandbox router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def get_test_db():
        yield db_session

    from app.core.storage.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.mark.api
class TestSandboxStartAPI:
    """Test cases for sandbox start API."""

    @pytest.mark.asyncio
    async def test_start_sandbox_session_not_found(self, app, db_session):
        """Test starting sandbox for non-existent session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/sandbox/nonexistent/start")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_sandbox_no_config(self, app, db_session, sample_chat_session):
        """Test starting sandbox without agent configuration."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/sandbox/{sample_chat_session.id}/start")

        assert response.status_code == 404
        assert "configuration" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_sandbox_success(
        self, app, db_session, sample_chat_session, sample_agent_config
    ):
        """Test successful sandbox start."""
        # The route accesses agent_config.environment_type and environment_config
        # which don't exist in the model - mock them on the config object
        sample_agent_config.environment_type = "python3.13"
        sample_agent_config.environment_config = {}
        await db_session.commit()

        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.container_id = "container-123"
            mock_manager.return_value.create_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/sandbox/{sample_chat_session.id}/start")

            assert response.status_code == 201
            data = response.json()
            assert "container_id" in data
            assert data["container_id"] == "container-123"

    @pytest.mark.asyncio
    async def test_start_sandbox_error(
        self, app, db_session, sample_chat_session, sample_agent_config
    ):
        """Test sandbox start failure."""
        # Mock the environment fields needed by the route
        sample_agent_config.environment_type = "python3.13"
        sample_agent_config.environment_config = {}
        await db_session.commit()

        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.create_container = AsyncMock(
                side_effect=Exception("Docker error")
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/sandbox/{sample_chat_session.id}/start")

            assert response.status_code == 500


@pytest.mark.api
class TestSandboxStopAPI:
    """Test cases for sandbox stop API."""

    @pytest.mark.asyncio
    async def test_stop_sandbox_success(self, app, db_session, sample_chat_session):
        """Test successful sandbox stop."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.destroy_container = AsyncMock(return_value=True)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/sandbox/{sample_chat_session.id}/stop")

            assert response.status_code == 200
            assert "stopped" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_stop_sandbox_not_running(self, app, db_session, sample_chat_session):
        """Test stopping sandbox that's not running."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.destroy_container = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/sandbox/{sample_chat_session.id}/stop")

            assert response.status_code == 200
            assert "not running" in response.json()["message"].lower()


@pytest.mark.api
class TestSandboxResetAPI:
    """Test cases for sandbox reset API."""

    @pytest.mark.asyncio
    async def test_reset_sandbox_success(self, app, db_session):
        """Test successful sandbox reset."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.reset_container = AsyncMock(return_value=True)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/sandbox/session-123/reset")

            assert response.status_code == 200
            assert "reset" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_reset_sandbox_not_found(self, app, db_session):
        """Test resetting non-existent sandbox."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.reset_container = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/sandbox/session-123/reset")

            assert response.status_code == 404


@pytest.mark.api
class TestSandboxStatusAPI:
    """Test cases for sandbox status API."""

    @pytest.mark.asyncio
    async def test_get_status_running(self, app, db_session):
        """Test getting status of running sandbox."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.container_id = "container-123"
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)
            mock_manager.return_value.get_container_stats.return_value = {"cpu": "10%"}

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/sandbox/session-123/status")

            assert response.status_code == 200
            data = response.json()
            assert data["running"] is True
            assert data["container_id"] == "container-123"

    @pytest.mark.asyncio
    async def test_get_status_not_running(self, app, db_session):
        """Test getting status of stopped sandbox."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.get_container = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/sandbox/session-123/status")

            assert response.status_code == 200
            data = response.json()
            assert data["running"] is False
            assert data["container_id"] is None


@pytest.mark.api
class TestSandboxExecuteAPI:
    """Test cases for sandbox execute API."""

    @pytest.mark.asyncio
    async def test_execute_not_running(self, app, db_session):
        """Test executing command when sandbox not running."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_manager.return_value.get_container = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/sandbox/session-123/execute", json={"command": "ls -la"}
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_success(self, app, db_session):
        """Test successful command execution."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_container.execute = AsyncMock(return_value=(0, "file.py\ntest.py", ""))
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/sandbox/session-123/execute",
                    json={"command": "ls -la", "workdir": "/workspace/out"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["exit_code"] == 0
            assert "file.py" in data["stdout"]

    @pytest.mark.asyncio
    async def test_execute_dangerous_command(self, app, db_session):
        """Test executing dangerous command."""
        with patch("app.api.routes.sandbox.get_container_manager") as mock_manager:
            mock_container = MagicMock()
            mock_manager.return_value.get_container = AsyncMock(return_value=mock_container)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/sandbox/session-123/execute", json={"command": "ls;rm -rf /"}
                )

            assert response.status_code == 400


@pytest.mark.unit
class TestSandboxModels:
    """Test cases for sandbox request/response models."""

    def test_execute_command_request(self):
        """Test ExecuteCommandRequest model."""
        request = ExecuteCommandRequest(command="ls -la")
        assert request.command == "ls -la"
        assert request.workdir == "/workspace"  # default

    def test_execute_command_request_with_workdir(self):
        """Test ExecuteCommandRequest with custom workdir."""
        request = ExecuteCommandRequest(command="pwd", workdir="/workspace/out")
        assert request.workdir == "/workspace/out"

    def test_execute_command_response(self):
        """Test ExecuteCommandResponse model."""
        response = ExecuteCommandResponse(
            exit_code=0,
            stdout="output",
            stderr="",
        )
        assert response.exit_code == 0
        assert response.stdout == "output"
        assert response.stderr == ""

    def test_container_status_response_running(self):
        """Test ContainerStatusResponse for running container."""
        response = ContainerStatusResponse(
            running=True,
            container_id="abc123",
            stats={"cpu": "10%"},
        )
        assert response.running is True
        assert response.container_id == "abc123"

    def test_container_status_response_stopped(self):
        """Test ContainerStatusResponse for stopped container."""
        response = ContainerStatusResponse(
            running=False,
            container_id=None,
            stats=None,
        )
        assert response.running is False
        assert response.container_id is None
