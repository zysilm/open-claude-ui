"""Tests for the StreamingManager module."""

import pytest
import asyncio
from unittest.mock import AsyncMock

from app.api.websocket.streaming_manager import StreamingManager


@pytest.mark.websocket
class TestStreamingManagerBasic:
    """Test basic StreamingManager functionality."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test StreamingManager initialization."""
        manager = StreamingManager()
        assert manager.active_streams == {}
        assert manager.cleanup_callbacks == {}
        assert manager._cleanup_task is None

    @pytest.mark.asyncio
    async def test_start_creates_cleanup_task(self):
        """Test that start() creates a background cleanup task."""
        manager = StreamingManager()
        await manager.start()

        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()

        # Clean up
        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_cleanup_task(self):
        """Test that stop() properly cancels the cleanup task."""
        manager = StreamingManager()
        await manager.start()
        await manager.stop()

        assert manager._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        """Test stop() when no cleanup task exists."""
        manager = StreamingManager()
        await manager.stop()  # Should not raise


@pytest.mark.websocket
class TestStreamingManagerRegister:
    """Test stream registration functionality."""

    @pytest.mark.asyncio
    async def test_register_stream(self):
        """Test registering a new stream."""
        manager = StreamingManager()
        cleanup_callback = AsyncMock()

        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=cleanup_callback
        )

        assert "session-123" in manager.active_streams
        stream_info = manager.active_streams["session-123"]
        assert stream_info["message_id"] == "msg-456"
        assert stream_info["finalized"] is False
        assert stream_info["content_length"] == 0
        assert "session-123" in manager.cleanup_callbacks
        assert manager.cleanup_callbacks["session-123"] == cleanup_callback

    @pytest.mark.asyncio
    async def test_register_multiple_streams(self):
        """Test registering multiple streams."""
        manager = StreamingManager()

        for i in range(3):
            await manager.register_stream(
                session_id=f"session-{i}", message_id=f"msg-{i}", cleanup_callback=AsyncMock()
            )

        assert len(manager.active_streams) == 3
        assert len(manager.cleanup_callbacks) == 3


@pytest.mark.websocket
class TestStreamingManagerActivity:
    """Test activity tracking functionality."""

    @pytest.mark.asyncio
    async def test_update_activity(self):
        """Test updating stream activity."""
        manager = StreamingManager()
        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=AsyncMock()
        )

        original_time = manager.active_streams["session-123"]["last_activity"]

        # Wait a bit and update
        await asyncio.sleep(0.01)
        await manager.update_activity("session-123", content_length=100)

        stream_info = manager.active_streams["session-123"]
        assert stream_info["content_length"] == 100
        assert stream_info["last_activity"] >= original_time

    @pytest.mark.asyncio
    async def test_update_activity_nonexistent_session(self):
        """Test updating activity for non-existent session (no-op)."""
        manager = StreamingManager()
        await manager.update_activity("nonexistent", content_length=100)
        # Should not raise, no-op

    @pytest.mark.asyncio
    async def test_update_activity_without_content_length(self):
        """Test updating activity without content length."""
        manager = StreamingManager()
        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=AsyncMock()
        )

        await manager.update_activity("session-123")

        # Content length should remain 0
        assert manager.active_streams["session-123"]["content_length"] == 0


@pytest.mark.websocket
class TestStreamingManagerFinalized:
    """Test finalization functionality."""

    @pytest.mark.asyncio
    async def test_mark_finalized(self):
        """Test marking stream as finalized."""
        manager = StreamingManager()
        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=AsyncMock()
        )

        assert manager.active_streams["session-123"]["finalized"] is False

        await manager.mark_finalized("session-123")

        assert manager.active_streams["session-123"]["finalized"] is True

    @pytest.mark.asyncio
    async def test_mark_finalized_nonexistent_session(self):
        """Test marking non-existent session as finalized (no-op)."""
        manager = StreamingManager()
        await manager.mark_finalized("nonexistent")
        # Should not raise


@pytest.mark.websocket
class TestStreamingManagerDisconnect:
    """Test disconnect handling functionality."""

    @pytest.mark.asyncio
    async def test_handle_disconnect_no_active_stream(self):
        """Test handling disconnect with no active stream."""
        manager = StreamingManager()
        await manager.handle_disconnect("nonexistent")
        # Should not raise

    @pytest.mark.asyncio
    async def test_handle_disconnect_already_finalized(self):
        """Test handling disconnect when stream is already finalized."""
        manager = StreamingManager()
        cleanup_callback = AsyncMock()

        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=cleanup_callback
        )
        await manager.mark_finalized("session-123")

        await manager.handle_disconnect("session-123")

        # Stream should be cleaned up
        assert "session-123" not in manager.active_streams
        assert "session-123" not in manager.cleanup_callbacks
        # Cleanup callback should NOT be called since already finalized
        cleanup_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_disconnect_waits_for_natural_completion(self):
        """Test that handle_disconnect waits for natural completion."""
        manager = StreamingManager()
        cleanup_callback = AsyncMock()

        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=cleanup_callback
        )

        # Simulate natural completion happening during wait
        async def finalize_later():
            await asyncio.sleep(0.5)
            await manager.mark_finalized("session-123")

        # Start both tasks
        disconnect_task = asyncio.create_task(manager.handle_disconnect("session-123"))
        finalize_task = asyncio.create_task(finalize_later())

        await disconnect_task
        await finalize_task

        # Stream should be cleaned up and callback NOT called
        assert "session-123" not in manager.active_streams
        cleanup_callback.assert_not_called()


@pytest.mark.websocket
class TestStreamingManagerCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_run_cleanup_executes_callback(self):
        """Test that cleanup executes the registered callback."""
        manager = StreamingManager()
        cleanup_callback = AsyncMock()

        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=cleanup_callback
        )

        await manager._run_cleanup("session-123")

        cleanup_callback.assert_called_once()
        assert "session-123" not in manager.active_streams
        assert "session-123" not in manager.cleanup_callbacks

    @pytest.mark.asyncio
    async def test_run_cleanup_handles_callback_error(self):
        """Test that cleanup handles callback errors gracefully."""
        manager = StreamingManager()
        cleanup_callback = AsyncMock(side_effect=Exception("Cleanup error"))

        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=cleanup_callback
        )

        # Should not raise
        await manager._run_cleanup("session-123")

        # Should still clean up tracking even on error
        assert "session-123" not in manager.active_streams
        assert "session-123" not in manager.cleanup_callbacks

    @pytest.mark.asyncio
    async def test_run_cleanup_no_callback(self):
        """Test cleanup when no callback is registered."""
        manager = StreamingManager()
        await manager._run_cleanup("nonexistent")
        # Should not raise


@pytest.mark.websocket
class TestStreamingManagerConcurrency:
    """Test concurrent access to StreamingManager."""

    @pytest.mark.asyncio
    async def test_concurrent_registrations(self):
        """Test concurrent stream registrations."""
        manager = StreamingManager()

        async def register(i):
            await manager.register_stream(
                session_id=f"session-{i}", message_id=f"msg-{i}", cleanup_callback=AsyncMock()
            )

        # Register 10 streams concurrently
        await asyncio.gather(*[register(i) for i in range(10)])

        assert len(manager.active_streams) == 10

    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """Test concurrent activity updates."""
        manager = StreamingManager()
        await manager.register_stream(
            session_id="session-123", message_id="msg-456", cleanup_callback=AsyncMock()
        )

        async def update(length):
            await manager.update_activity("session-123", content_length=length)

        # Update 100 times concurrently
        await asyncio.gather(*[update(i) for i in range(100)])

        # Final content length should be one of the values
        assert manager.active_streams["session-123"]["content_length"] in range(100)
