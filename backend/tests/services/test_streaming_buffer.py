"""Tests for StreamingBuffer service."""

import pytest
import time

from app.services.streaming_buffer import StreamingBuffer, StreamMetadata


@pytest.mark.unit
class TestStreamMetadata:
    """Test cases for StreamMetadata."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = StreamMetadata()

        assert metadata.chunk_count == 0
        assert metadata.total_bytes == 0
        assert metadata.is_streaming is True
        assert metadata.end_time is None
        assert metadata.error is None
        assert metadata.start_time is not None


@pytest.mark.unit
class TestStreamingBuffer:
    """Test cases for StreamingBuffer."""

    def test_init(self):
        """Test buffer initialization."""
        buffer = StreamingBuffer()
        assert buffer.max_buffer_size == 10000

        buffer = StreamingBuffer(max_buffer_size=5000)
        assert buffer.max_buffer_size == 5000

    def test_start_streaming(self):
        """Test starting a streaming session."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)

        assert message_id in buffer._buffers
        assert message_id in buffer._metadata
        assert buffer._metadata[message_id].is_streaming is True

    def test_add_chunk(self):
        """Test adding chunks to buffer."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "Hello")
        buffer.add_chunk(message_id, " World")

        assert len(buffer._buffers[message_id]) == 2
        assert buffer._metadata[message_id].chunk_count == 2
        assert buffer._metadata[message_id].total_bytes == 11

    def test_add_chunk_no_active_stream(self):
        """Test adding chunk without active stream."""
        buffer = StreamingBuffer()

        with pytest.raises(ValueError) as exc_info:
            buffer.add_chunk("nonexistent", "chunk")

        assert "No active stream" in str(exc_info.value)

    def test_add_chunk_buffer_overflow(self):
        """Test buffer overflow handling."""
        buffer = StreamingBuffer(max_buffer_size=100)
        message_id = "msg-123"

        buffer.start_streaming(message_id)

        # Add chunks to exceed buffer size
        for i in range(150):
            buffer.add_chunk(message_id, f"chunk{i}")

        # Buffer should be truncated to last 1000 (or less if max is lower)
        assert len(buffer._buffers[message_id]) <= 1000

    def test_get_complete_content(self):
        """Test getting complete content."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "Hello")
        buffer.add_chunk(message_id, " ")
        buffer.add_chunk(message_id, "World")

        content = buffer.get_complete_content(message_id)
        assert content == "Hello World"

    def test_get_complete_content_no_buffer(self):
        """Test getting content for non-existent buffer."""
        buffer = StreamingBuffer()
        content = buffer.get_complete_content("nonexistent")
        assert content == ""

    def test_get_chunks_since(self):
        """Test getting chunks since an index."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        for i in range(5):
            buffer.add_chunk(message_id, f"chunk{i}")

        # Get chunks from index 2
        chunks = buffer.get_chunks_since(message_id, 2)
        assert len(chunks) == 3
        assert chunks == ["chunk2", "chunk3", "chunk4"]

    def test_get_chunks_since_no_buffer(self):
        """Test getting chunks for non-existent buffer."""
        buffer = StreamingBuffer()
        chunks = buffer.get_chunks_since("nonexistent", 0)
        assert chunks == []

    def test_get_metadata(self):
        """Test getting streaming metadata."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "test")

        metadata = buffer.get_metadata(message_id)

        assert metadata is not None
        assert metadata.chunk_count == 1
        assert metadata.total_bytes == 4

    def test_get_metadata_not_found(self):
        """Test getting metadata for non-existent message."""
        buffer = StreamingBuffer()
        metadata = buffer.get_metadata("nonexistent")
        assert metadata is None

    def test_end_streaming(self):
        """Test ending a streaming session."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "test content")
        time.sleep(0.01)  # Small delay for duration calculation

        result = buffer.end_streaming(message_id)

        assert result["chunk_count"] == 1
        assert result["total_bytes"] == 12
        assert result["is_streaming"] is False
        assert result["duration"] > 0
        assert result["error"] is None

    def test_end_streaming_with_error(self):
        """Test ending streaming with error."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        result = buffer.end_streaming(message_id, error="Connection lost")

        assert result["error"] == "Connection lost"

    def test_end_streaming_not_found(self):
        """Test ending streaming for non-existent message."""
        buffer = StreamingBuffer()
        result = buffer.end_streaming("nonexistent")
        assert result == {}

    def test_cleanup(self):
        """Test cleaning up a buffer."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "test")

        buffer.cleanup(message_id)

        assert message_id not in buffer._buffers
        assert message_id not in buffer._metadata

    def test_get_active_streams(self):
        """Test getting active streams."""
        buffer = StreamingBuffer()

        buffer.start_streaming("msg-1")
        buffer.start_streaming("msg-2")
        buffer.start_streaming("msg-3")
        buffer.end_streaming("msg-2")

        active = buffer.get_active_streams()

        assert len(active) == 2
        assert "msg-1" in active
        assert "msg-3" in active
        assert "msg-2" not in active

    def test_get_memory_usage(self):
        """Test getting memory usage stats."""
        buffer = StreamingBuffer()

        buffer.start_streaming("msg-1")
        buffer.add_chunk("msg-1", "hello")  # 5 bytes
        buffer.add_chunk("msg-1", "world")  # 5 bytes

        buffer.start_streaming("msg-2")
        buffer.add_chunk("msg-2", "test")  # 4 bytes

        usage = buffer.get_memory_usage()

        assert usage["buffer_count"] == 2
        assert usage["total_chunks"] == 3
        assert usage["total_bytes"] == 14
        assert usage["active_streams"] == 2

    def test_has_buffer(self):
        """Test checking if buffer exists."""
        buffer = StreamingBuffer()

        assert buffer.has_buffer("msg-123") is False

        buffer.start_streaming("msg-123")
        assert buffer.has_buffer("msg-123") is True

    def test_reset_buffer(self):
        """Test resetting a buffer."""
        buffer = StreamingBuffer()
        message_id = "msg-123"

        buffer.start_streaming(message_id)
        buffer.add_chunk(message_id, "chunk1")
        buffer.add_chunk(message_id, "chunk2")

        buffer.reset_buffer(message_id)

        assert len(buffer._buffers[message_id]) == 0
        assert buffer._metadata[message_id].chunk_count == 0
        assert buffer._metadata[message_id].total_bytes == 0

    def test_reset_nonexistent_buffer(self):
        """Test resetting non-existent buffer (should not raise)."""
        buffer = StreamingBuffer()
        buffer.reset_buffer("nonexistent")  # Should not raise
