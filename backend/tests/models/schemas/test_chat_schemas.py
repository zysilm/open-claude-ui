"""Tests for Chat Session Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.schemas.chat import (
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionListResponse,
)
from app.models.database.chat_session import ChatSessionStatus


@pytest.mark.unit
class TestChatSessionSchemas:
    """Test cases for ChatSession schemas."""

    def test_chat_session_base_valid(self):
        """Test valid ChatSessionBase schema."""
        session = ChatSessionBase(name="Test Session")
        assert session.name == "Test Session"

    def test_chat_session_base_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChatSessionBase(name="")

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_chat_session_base_name_too_long(self):
        """Test that name exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChatSessionBase(name="x" * 256)

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_long" for e in errors)

    def test_chat_session_create(self):
        """Test ChatSessionCreate schema."""
        session = ChatSessionCreate(name="New Session")
        assert session.name == "New Session"

    def test_chat_session_update_name(self):
        """Test ChatSessionUpdate with name."""
        update = ChatSessionUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.status is None

    def test_chat_session_update_status(self):
        """Test ChatSessionUpdate with status."""
        update = ChatSessionUpdate(status=ChatSessionStatus.ARCHIVED)
        assert update.name is None
        assert update.status == ChatSessionStatus.ARCHIVED

    def test_chat_session_update_all(self):
        """Test ChatSessionUpdate with all fields."""
        update = ChatSessionUpdate(
            name="New Name",
            status=ChatSessionStatus.ACTIVE,
        )
        assert update.name == "New Name"
        assert update.status == ChatSessionStatus.ACTIVE

    def test_chat_session_update_empty(self):
        """Test ChatSessionUpdate with no fields."""
        update = ChatSessionUpdate()
        assert update.name is None
        assert update.status is None

    def test_chat_session_response(self):
        """Test ChatSessionResponse schema."""
        now = datetime.utcnow()
        response = ChatSessionResponse(
            id="session-id-123",
            project_id="project-id-456",
            name="Test Session",
            created_at=now,
            updated_at=now,
            container_id=None,
            status=ChatSessionStatus.ACTIVE,
            environment_type=None,
        )
        assert response.id == "session-id-123"
        assert response.project_id == "project-id-456"
        assert response.status == ChatSessionStatus.ACTIVE
        assert response.environment_type is None

    def test_chat_session_response_with_environment(self):
        """Test ChatSessionResponse with environment type."""
        now = datetime.utcnow()
        response = ChatSessionResponse(
            id="session-id",
            project_id="project-id",
            name="Python Session",
            created_at=now,
            updated_at=now,
            container_id="container-abc123",
            status=ChatSessionStatus.ACTIVE,
            environment_type="python3.13",
        )
        assert response.container_id == "container-abc123"
        assert response.environment_type == "python3.13"

    def test_chat_session_response_from_attributes(self):
        """Test ChatSessionResponse with from_attributes config."""

        class MockSession:
            id = "mock-session-id"
            project_id = "mock-project-id"
            name = "Mock Session"
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()
            container_id = None
            status = ChatSessionStatus.ACTIVE
            environment_type = None

        response = ChatSessionResponse.model_validate(MockSession())
        assert response.id == "mock-session-id"
        assert response.status == ChatSessionStatus.ACTIVE

    def test_chat_session_list_response(self):
        """Test ChatSessionListResponse schema."""
        now = datetime.utcnow()
        sessions = [
            ChatSessionResponse(
                id=f"session-{i}",
                project_id="project-id",
                name=f"Session {i}",
                created_at=now,
                updated_at=now,
                container_id=None,
                status=ChatSessionStatus.ACTIVE,
                environment_type=None,
            )
            for i in range(5)
        ]
        response = ChatSessionListResponse(chat_sessions=sessions, total=20)

        assert len(response.chat_sessions) == 5
        assert response.total == 20
        assert response.chat_sessions[0].name == "Session 0"

    def test_chat_session_list_response_empty(self):
        """Test ChatSessionListResponse with empty list."""
        response = ChatSessionListResponse(chat_sessions=[], total=0)
        assert len(response.chat_sessions) == 0
        assert response.total == 0
