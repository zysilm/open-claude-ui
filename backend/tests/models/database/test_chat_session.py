"""Tests for ChatSession database model."""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.database import ChatSession
from app.models.database.chat_session import ChatSessionStatus


@pytest.mark.unit
class TestChatSessionModel:
    """Test cases for the ChatSession model."""

    @pytest.mark.asyncio
    async def test_create_chat_session(self, db_session, sample_project):
        """Test creating a new chat session."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Test Chat Session",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert len(session.id) == 36
        assert session.project_id == sample_project.id
        assert session.name == "Test Chat Session"
        assert session.status == ChatSessionStatus.ACTIVE
        assert session.container_id is None
        assert session.environment_type is None

    @pytest.mark.asyncio
    async def test_chat_session_status_enum(self, db_session, sample_project):
        """Test ChatSession status enum values."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Status Test",
            status=ChatSessionStatus.ARCHIVED,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ChatSessionStatus.ARCHIVED
        assert session.status.value == "archived"

    @pytest.mark.asyncio
    async def test_chat_session_with_container(self, db_session, sample_project):
        """Test chat session with container ID."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Container Session",
            container_id="abc123container",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.container_id == "abc123container"

    @pytest.mark.asyncio
    async def test_chat_session_environment(self, db_session, sample_project):
        """Test chat session with environment settings."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Python Session",
            environment_type="python3.13",
            environment_config={"packages": ["numpy", "pandas"]},
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.environment_type == "python3.13"
        assert session.environment_config == {"packages": ["numpy", "pandas"]}

    @pytest.mark.asyncio
    async def test_chat_session_title_auto_generated(self, db_session, sample_project):
        """Test title_auto_generated flag."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Auto Title Session",
            title_auto_generated="Y",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.title_auto_generated == "Y"

    @pytest.mark.asyncio
    async def test_chat_session_timestamps(self, db_session, sample_project):
        """Test chat session timestamps."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Timestamp Test",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_chat_session_project_relationship(self, db_session, sample_project):
        """Test chat session relationship with project."""
        session = ChatSession(
            project_id=sample_project.id,
            name="Relationship Test",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Access the relationship
        assert session.project.id == sample_project.id
        assert session.project.name == sample_project.name

    @pytest.mark.asyncio
    async def test_multiple_chat_sessions_per_project(self, db_session, sample_project):
        """Test creating multiple chat sessions for one project."""
        sessions = [
            ChatSession(project_id=sample_project.id, name=f"Session {i}") for i in range(3)
        ]
        db_session.add_all(sessions)
        await db_session.commit()

        query = select(ChatSession).where(ChatSession.project_id == sample_project.id)
        result = await db_session.execute(query)
        all_sessions = result.scalars().all()

        assert len(all_sessions) == 3

    @pytest.mark.asyncio
    async def test_chat_session_delete(self, db_session, sample_chat_session):
        """Test deleting a chat session."""
        session_id = sample_chat_session.id
        await db_session.delete(sample_chat_session)
        await db_session.commit()

        query = select(ChatSession).where(ChatSession.id == session_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()

        assert deleted is None

    @pytest.mark.asyncio
    async def test_status_enum_values(self):
        """Test all ChatSessionStatus enum values."""
        assert ChatSessionStatus.ACTIVE.value == "active"
        assert ChatSessionStatus.ARCHIVED.value == "archived"
        assert len(ChatSessionStatus) == 2
