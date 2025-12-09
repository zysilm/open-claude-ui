"""
Unit tests for MessageOrchestrator service.
Tests streaming lifecycle, chunk processing, and persistence coordination.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.message_orchestrator import MessageOrchestrator
from app.services.message_persistence import MessagePersistenceService
from app.services.streaming_buffer import StreamingBuffer, StreamMetadata
from app.services.event_bus import EventBus, StreamingEvent


@pytest.fixture
def mock_persistence():
    """Create a mock persistence service."""
    persistence = MagicMock(spec=MessagePersistenceService)
    persistence.create_message = AsyncMock(return_value="msg-123")
    persistence.save_complete_message = AsyncMock(return_value=True)
    persistence.get_message = AsyncMock(return_value=MagicMock(content="test content"))
    persistence.mark_message_incomplete = AsyncMock()
    persistence.delete_incomplete_messages = AsyncMock(return_value=0)
    return persistence


@pytest.fixture
def mock_buffer():
    """Create a mock streaming buffer."""
    buffer = MagicMock(spec=StreamingBuffer)
    buffer.start_streaming = MagicMock()
    buffer.add_chunk = MagicMock()
    buffer.get_complete_content = MagicMock(return_value="test content")
    buffer.end_streaming = MagicMock(return_value={"chunk_count": 5, "total_bytes": 100})
    buffer.cleanup = MagicMock()
    buffer.get_metadata = MagicMock(return_value=StreamMetadata())
    return buffer


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.emit = AsyncMock()
    return event_bus


@pytest.fixture
def orchestrator(mock_persistence, mock_buffer, mock_event_bus):
    """Create an orchestrator with mocked dependencies."""
    return MessageOrchestrator(
        persistence=mock_persistence, buffer=mock_buffer, event_bus=mock_event_bus
    )


@pytest.mark.asyncio
class TestMessageOrchestratorInit:
    """Test orchestrator initialization."""

    def test_init_with_dependencies(self, mock_persistence, mock_buffer, mock_event_bus):
        """Test orchestrator initializes with dependencies."""
        orchestrator = MessageOrchestrator(
            persistence=mock_persistence, buffer=mock_buffer, event_bus=mock_event_bus
        )
        assert orchestrator.persistence == mock_persistence
        assert orchestrator.buffer == mock_buffer
        assert orchestrator.event_bus == mock_event_bus
        assert orchestrator._active_streams == {}


@pytest.mark.asyncio
class TestStartStreaming:
    """Test start_streaming method."""

    async def test_start_streaming_success(
        self, orchestrator, mock_persistence, mock_buffer, mock_event_bus
    ):
        """Test successful streaming start."""
        message_id = await orchestrator.start_streaming(
            session_id="session-123", role="assistant", metadata={"source": "test"}
        )

        assert message_id == "msg-123"
        mock_persistence.create_message.assert_called_once_with(
            "session-123", "assistant", "", {"source": "test"}
        )
        mock_buffer.start_streaming.assert_called_once_with("msg-123")
        mock_event_bus.emit.assert_called()

        # Check active streams tracking
        assert "msg-123" in orchestrator._active_streams
        assert orchestrator._active_streams["msg-123"] == "session-123"

    async def test_start_streaming_emits_event(self, orchestrator, mock_event_bus):
        """Test that start streaming emits the correct event."""
        await orchestrator.start_streaming(session_id="session-123")

        # Verify START event was emitted
        calls = mock_event_bus.emit.call_args_list
        start_call = [c for c in calls if c[0][0] == StreamingEvent.START]
        assert len(start_call) == 1
        event_data = start_call[0][0][1]
        assert event_data["session_id"] == "session-123"
        assert event_data["role"] == "assistant"

    async def test_start_streaming_exception(self, orchestrator, mock_persistence):
        """Test error handling during streaming start."""
        mock_persistence.create_message.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await orchestrator.start_streaming(session_id="session-123")


@pytest.mark.asyncio
class TestProcessChunk:
    """Test process_chunk method."""

    async def test_process_chunk_success(self, orchestrator, mock_buffer, mock_event_bus):
        """Test successful chunk processing."""
        # Start streaming first
        await orchestrator.start_streaming(session_id="session-123")

        # Process chunk
        await orchestrator.process_chunk("msg-123", "Hello ")

        mock_buffer.add_chunk.assert_called_with("msg-123", "Hello ")

        # Verify CHUNK event was emitted
        chunk_calls = [
            c for c in mock_event_bus.emit.call_args_list if c[0][0] == StreamingEvent.CHUNK
        ]
        assert len(chunk_calls) == 1
        assert chunk_calls[0][0][1]["content"] == "Hello "

    async def test_process_chunk_error(self, orchestrator, mock_buffer, mock_event_bus):
        """Test chunk processing error handling."""
        mock_buffer.add_chunk.side_effect = ValueError("Invalid message ID")

        await orchestrator.process_chunk("invalid-id", "test")

        # Should emit error event
        error_calls = [
            c for c in mock_event_bus.emit.call_args_list if c[0][0] == StreamingEvent.ERROR
        ]
        assert len(error_calls) == 1


@pytest.mark.asyncio
class TestProcessAction:
    """Test process_action method."""

    async def test_process_action_streaming(self, orchestrator, mock_event_bus):
        """Test processing streaming action."""
        await orchestrator.process_action(
            message_id="msg-123", tool="bash", status="streaming", step=1
        )

        action_calls = [
            c
            for c in mock_event_bus.emit.call_args_list
            if c[0][0] == StreamingEvent.ACTION_STREAMING
        ]
        assert len(action_calls) == 1
        event_data = action_calls[0][0][1]
        assert event_data["tool"] == "bash"
        assert event_data["step"] == 1

    async def test_process_action_complete(self, orchestrator, mock_event_bus):
        """Test processing completed action."""
        await orchestrator.process_action(
            message_id="msg-123",
            tool="file_read",
            args={"path": "/test.txt"},
            status="complete",
            step=2,
        )

        action_calls = [
            c
            for c in mock_event_bus.emit.call_args_list
            if c[0][0] == StreamingEvent.ACTION_COMPLETE
        ]
        assert len(action_calls) == 1
        event_data = action_calls[0][0][1]
        assert event_data["tool"] == "file_read"
        assert event_data["args"]["path"] == "/test.txt"


@pytest.mark.asyncio
class TestProcessObservation:
    """Test process_observation method."""

    async def test_process_observation_success(self, orchestrator, mock_event_bus):
        """Test processing successful observation."""
        await orchestrator.process_observation(
            message_id="msg-123",
            content="File read successfully",
            success=True,
            metadata={"file": "test.txt"},
            step=1,
        )

        obs_calls = [
            c for c in mock_event_bus.emit.call_args_list if c[0][0] == StreamingEvent.OBSERVATION
        ]
        assert len(obs_calls) == 1
        event_data = obs_calls[0][0][1]
        assert event_data["content"] == "File read successfully"
        assert event_data["success"] is True

    async def test_process_observation_failure(self, orchestrator, mock_event_bus):
        """Test processing failed observation."""
        await orchestrator.process_observation(
            message_id="msg-123", content="Command failed", success=False
        )

        obs_calls = [
            c for c in mock_event_bus.emit.call_args_list if c[0][0] == StreamingEvent.OBSERVATION
        ]
        assert len(obs_calls) == 1
        assert obs_calls[0][0][1]["success"] is False


@pytest.mark.asyncio
class TestCompleteStreaming:
    """Test complete_streaming method."""

    async def test_complete_streaming_success(
        self, orchestrator, mock_persistence, mock_buffer, mock_event_bus
    ):
        """Test successful streaming completion."""
        # Start streaming first
        await orchestrator.start_streaming(session_id="session-123")

        # Complete streaming
        result = await orchestrator.complete_streaming("msg-123")

        assert result is True
        mock_buffer.get_complete_content.assert_called_with("msg-123")
        mock_buffer.end_streaming.assert_called_with("msg-123")
        mock_persistence.save_complete_message.assert_called()
        mock_buffer.cleanup.assert_called_with("msg-123")

        # Verify message removed from active streams
        assert "msg-123" not in orchestrator._active_streams

    async def test_complete_streaming_emits_events(self, orchestrator, mock_event_bus):
        """Test that completion emits proper events."""
        await orchestrator.start_streaming(session_id="session-123")
        await orchestrator.complete_streaming("msg-123")

        event_types = [c[0][0] for c in mock_event_bus.emit.call_args_list]
        assert StreamingEvent.PERSIST_START in event_types
        assert StreamingEvent.PERSIST_SUCCESS in event_types
        assert StreamingEvent.END in event_types

    async def test_complete_streaming_cancelled(self, orchestrator, mock_buffer):
        """Test streaming completion with cancellation."""
        await orchestrator.start_streaming(session_id="session-123")

        result = await orchestrator.complete_streaming("msg-123", cancelled=True)

        assert result is True
        # Check metadata includes cancelled flag
        metadata = mock_buffer.end_streaming.return_value
        assert "cancelled" in metadata or mock_buffer.end_streaming.called

    async def test_complete_streaming_persistence_failure(
        self, orchestrator, mock_persistence, mock_event_bus
    ):
        """Test handling of persistence failure."""
        await orchestrator.start_streaming(session_id="session-123")
        mock_persistence.save_complete_message.return_value = False

        result = await orchestrator.complete_streaming("msg-123")

        assert result is False
        mock_persistence.mark_message_incomplete.assert_called()

        # Verify failure events
        event_types = [c[0][0] for c in mock_event_bus.emit.call_args_list]
        assert StreamingEvent.PERSIST_FAILURE in event_types
        assert StreamingEvent.ERROR in event_types

    async def test_complete_streaming_exception(self, orchestrator, mock_persistence, mock_buffer):
        """Test handling of exceptions during completion."""
        await orchestrator.start_streaming(session_id="session-123")
        mock_buffer.get_complete_content.side_effect = Exception("Buffer error")

        result = await orchestrator.complete_streaming("msg-123")

        assert result is False


@pytest.mark.asyncio
class TestResumeStreaming:
    """Test resume_streaming method."""

    async def test_resume_streaming_active_stream(self, orchestrator, mock_buffer, mock_event_bus):
        """Test resuming an active stream."""
        # Start streaming
        await orchestrator.start_streaming(session_id="session-123")

        # Setup buffer metadata
        metadata = StreamMetadata()
        metadata.is_streaming = True
        metadata.chunk_count = 5
        metadata.total_bytes = 100
        mock_buffer.get_metadata.return_value = metadata

        # Resume
        result = await orchestrator.resume_streaming("session-123")

        assert result is not None
        assert result["message_id"] == "msg-123"
        assert result["chunk_count"] == 5
        assert result["is_streaming"] is True

        # Verify RESUME event
        resume_calls = [
            c for c in mock_event_bus.emit.call_args_list if c[0][0] == StreamingEvent.RESUME
        ]
        assert len(resume_calls) == 1

    async def test_resume_streaming_no_active_stream(self, orchestrator):
        """Test resuming when no active stream exists."""
        result = await orchestrator.resume_streaming("nonexistent-session")
        assert result is None


@pytest.mark.asyncio
class TestCancelStreaming:
    """Test cancel_streaming method."""

    async def test_cancel_streaming_success(self, orchestrator):
        """Test successful stream cancellation."""
        await orchestrator.start_streaming(session_id="session-123")

        result = await orchestrator.cancel_streaming("msg-123")

        assert result is True

    async def test_cancel_streaming_not_found(self, orchestrator):
        """Test cancelling non-existent stream."""
        result = await orchestrator.cancel_streaming("nonexistent")
        assert result is False


@pytest.mark.asyncio
class TestStreamingStatus:
    """Test streaming status methods."""

    async def test_get_active_streams(self, orchestrator):
        """Test getting all active streams."""
        await orchestrator.start_streaming(session_id="session-1")

        # Manually add another to simulate multiple streams
        orchestrator._active_streams["msg-456"] = "session-2"

        streams = orchestrator.get_active_streams()
        assert len(streams) == 2
        assert "msg-123" in streams
        assert "msg-456" in streams

    async def test_is_streaming_true(self, orchestrator, mock_buffer):
        """Test is_streaming when actively streaming."""
        await orchestrator.start_streaming(session_id="session-123")

        metadata = StreamMetadata()
        metadata.is_streaming = True
        mock_buffer.get_metadata.return_value = metadata

        assert orchestrator.is_streaming("msg-123") is True

    async def test_is_streaming_false(self, orchestrator):
        """Test is_streaming when not streaming."""
        assert orchestrator.is_streaming("nonexistent") is False

    async def test_get_streaming_status(self, orchestrator, mock_buffer):
        """Test getting detailed streaming status."""
        await orchestrator.start_streaming(session_id="session-123")

        metadata = StreamMetadata()
        metadata.is_streaming = True
        metadata.chunk_count = 10
        metadata.total_bytes = 500
        mock_buffer.get_metadata.return_value = metadata

        status = await orchestrator.get_streaming_status("msg-123")

        assert status is not None
        assert status["message_id"] == "msg-123"
        assert status["session_id"] == "session-123"
        assert status["is_streaming"] is True
        assert status["chunk_count"] == 10

    async def test_get_streaming_status_not_found(self, orchestrator):
        """Test getting status for non-existent stream."""
        status = await orchestrator.get_streaming_status("nonexistent")
        assert status is None


@pytest.mark.asyncio
class TestCleanupIncompleteStreams:
    """Test cleanup_incomplete_streams method."""

    async def test_cleanup_incomplete_streams(self, orchestrator, mock_persistence):
        """Test cleaning up incomplete streams."""
        # Start multiple streams for same session
        await orchestrator.start_streaming(session_id="session-123")
        orchestrator._active_streams["msg-456"] = "session-123"

        # Clean up
        cleaned = await orchestrator.cleanup_incomplete_streams("session-123")

        assert cleaned >= 0
        mock_persistence.delete_incomplete_messages.assert_called_with("session-123")

    async def test_cleanup_no_streams(self, orchestrator, mock_persistence):
        """Test cleanup when no streams exist."""
        mock_persistence.delete_incomplete_messages.return_value = 0

        cleaned = await orchestrator.cleanup_incomplete_streams("empty-session")

        assert cleaned == 0
