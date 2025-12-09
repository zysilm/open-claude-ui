"""Tests for the AgentTaskRegistry module."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.api.websocket.task_registry import (
    AgentTask,
    AgentTaskRegistry,
    get_agent_task_registry,
)


@pytest.mark.websocket
class TestAgentTask:
    """Test AgentTask dataclass."""

    def test_agent_task_creation(self):
        """Test creating an AgentTask."""
        task = MagicMock(spec=asyncio.Task)
        cancel_event = asyncio.Event()

        agent_task = AgentTask(
            task=task,
            session_id="session-123",
            message_id="msg-456",
            cancel_event=cancel_event,
            created_at=datetime.utcnow(),
            status="running",
        )

        assert agent_task.session_id == "session-123"
        assert agent_task.message_id == "msg-456"
        assert agent_task.status == "running"
        assert agent_task.task == task
        assert agent_task.cancel_event == cancel_event

    def test_agent_task_status_values(self):
        """Test AgentTask can hold different status values."""
        task = MagicMock(spec=asyncio.Task)

        for status in ["running", "completed", "error", "cancelled"]:
            agent_task = AgentTask(
                task=task,
                session_id="session-123",
                message_id="msg-456",
                cancel_event=asyncio.Event(),
                created_at=datetime.utcnow(),
                status=status,
            )
            assert agent_task.status == status


@pytest.mark.websocket
class TestAgentTaskRegistryBasic:
    """Test basic AgentTaskRegistry functionality."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test AgentTaskRegistry initialization."""
        registry = AgentTaskRegistry()
        assert registry._tasks == {}

    @pytest.mark.asyncio
    async def test_register_task(self):
        """Test registering a new task."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        agent_task = await registry.get_task("session-123")
        assert agent_task is not None
        assert agent_task.session_id == "session-123"
        assert agent_task.message_id == "msg-456"
        assert agent_task.status == "running"

    @pytest.mark.asyncio
    async def test_register_task_replaces_existing(self):
        """Test that registering a task cancels existing task for same session."""
        registry = AgentTaskRegistry()

        # Register first task
        old_task = MagicMock(spec=asyncio.Task)
        old_task.done.return_value = False
        old_cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123",
            message_id="msg-old",
            task=old_task,
            cancel_event=old_cancel_event,
        )

        # Register new task for same session
        new_task = MagicMock(spec=asyncio.Task)
        new_task.done.return_value = False
        new_cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123",
            message_id="msg-new",
            task=new_task,
            cancel_event=new_cancel_event,
        )

        # Old task should be cancelled
        assert old_cancel_event.is_set()
        old_task.cancel.assert_called_once()

        # New task should be registered
        agent_task = await registry.get_task("session-123")
        assert agent_task.message_id == "msg-new"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting a non-existent task."""
        registry = AgentTaskRegistry()
        result = await registry.get_task("nonexistent")
        assert result is None


@pytest.mark.websocket
class TestAgentTaskRegistryCancel:
    """Test task cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        """Test cancelling a running task."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        result = await registry.cancel_task("session-123")

        assert result is True
        assert cancel_event.is_set()
        task.cancel.assert_called_once()

        agent_task = await registry.get_task("session-123")
        assert agent_task.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_task_already_done(self):
        """Test cancelling an already completed task."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = True  # Already done
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        result = await registry.cancel_task("session-123")

        assert result is False
        assert not cancel_event.is_set()
        task.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test cancelling a non-existent task."""
        registry = AgentTaskRegistry()
        result = await registry.cancel_task("nonexistent")
        assert result is False


@pytest.mark.websocket
class TestAgentTaskRegistryStatus:
    """Test task status management."""

    @pytest.mark.asyncio
    async def test_mark_completed(self):
        """Test marking a task as completed."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        await registry.mark_completed("session-123")

        agent_task = await registry.get_task("session-123")
        assert agent_task.status == "completed"

    @pytest.mark.asyncio
    async def test_mark_completed_with_error(self):
        """Test marking a task as completed with error status."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        await registry.mark_completed("session-123", status="error")

        agent_task = await registry.get_task("session-123")
        assert agent_task.status == "error"

    @pytest.mark.asyncio
    async def test_mark_completed_not_found(self):
        """Test marking a non-existent task as completed."""
        registry = AgentTaskRegistry()
        await registry.mark_completed("nonexistent")  # Should not raise


@pytest.mark.websocket
class TestAgentTaskRegistryCleanup:
    """Test task cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_task(self):
        """Test removing a task from registry."""
        registry = AgentTaskRegistry()

        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False
        cancel_event = asyncio.Event()

        await registry.register_task(
            session_id="session-123", message_id="msg-456", task=task, cancel_event=cancel_event
        )

        await registry.cleanup_task("session-123")

        result = await registry.get_task("session-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_task_not_found(self):
        """Test cleaning up a non-existent task."""
        registry = AgentTaskRegistry()
        await registry.cleanup_task("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self):
        """Test cleaning up old completed tasks."""
        registry = AgentTaskRegistry()

        # Create an old task
        old_task = MagicMock(spec=asyncio.Task)
        old_task.done.return_value = True

        # Create a recent task
        recent_task = MagicMock(spec=asyncio.Task)
        recent_task.done.return_value = True

        await registry.register_task(
            session_id="old-session",
            message_id="msg-old",
            task=old_task,
            cancel_event=asyncio.Event(),
        )

        await registry.register_task(
            session_id="recent-session",
            message_id="msg-recent",
            task=recent_task,
            cancel_event=asyncio.Event(),
        )

        # Manually set old task's created_at to be old
        registry._tasks["old-session"].created_at = datetime.utcnow() - timedelta(hours=2)

        # Cleanup tasks older than 1 hour
        count = await registry.cleanup_old_tasks(max_age_seconds=3600)

        assert count == 1
        assert await registry.get_task("old-session") is None
        assert await registry.get_task("recent-session") is not None

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks_running_not_cleaned(self):
        """Test that running tasks are not cleaned up."""
        registry = AgentTaskRegistry()

        # Create an old but still running task
        old_task = MagicMock(spec=asyncio.Task)
        old_task.done.return_value = False  # Still running

        await registry.register_task(
            session_id="old-session",
            message_id="msg-old",
            task=old_task,
            cancel_event=asyncio.Event(),
        )

        # Manually set old task's created_at to be old
        registry._tasks["old-session"].created_at = datetime.utcnow() - timedelta(hours=2)

        # Cleanup should not affect running tasks
        count = await registry.cleanup_old_tasks(max_age_seconds=3600)

        assert count == 0
        assert await registry.get_task("old-session") is not None


@pytest.mark.websocket
class TestAgentTaskRegistryConcurrency:
    """Test concurrent access to AgentTaskRegistry."""

    @pytest.mark.asyncio
    async def test_concurrent_registrations(self):
        """Test concurrent task registrations."""
        registry = AgentTaskRegistry()

        async def register(i):
            task = MagicMock(spec=asyncio.Task)
            task.done.return_value = False
            await registry.register_task(
                session_id=f"session-{i}",
                message_id=f"msg-{i}",
                task=task,
                cancel_event=asyncio.Event(),
            )

        # Register 10 tasks concurrently
        await asyncio.gather(*[register(i) for i in range(10)])

        # All 10 should be registered
        for i in range(10):
            task = await registry.get_task(f"session-{i}")
            assert task is not None

    @pytest.mark.asyncio
    async def test_concurrent_cancellations(self):
        """Test concurrent task cancellations."""
        registry = AgentTaskRegistry()

        # Register multiple tasks
        for i in range(10):
            task = MagicMock(spec=asyncio.Task)
            task.done.return_value = False
            await registry.register_task(
                session_id=f"session-{i}",
                message_id=f"msg-{i}",
                task=task,
                cancel_event=asyncio.Event(),
            )

        async def cancel(i):
            return await registry.cancel_task(f"session-{i}")

        # Cancel all concurrently
        results = await asyncio.gather(*[cancel(i) for i in range(10)])

        # All should be cancelled
        assert all(results)


@pytest.mark.websocket
class TestAgentTaskRegistrySingleton:
    """Test singleton instance functionality."""

    def test_get_agent_task_registry_returns_singleton(self):
        """Test that get_agent_task_registry returns the same instance."""
        # Reset singleton for test
        import app.api.websocket.task_registry as module

        original = module._agent_task_registry
        module._agent_task_registry = None

        try:
            registry1 = get_agent_task_registry()
            registry2 = get_agent_task_registry()

            assert registry1 is registry2
        finally:
            # Restore original
            module._agent_task_registry = original
