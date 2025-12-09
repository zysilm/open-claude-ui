"""Tests for EventBus service."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.services.event_bus import (
    EventBus,
    StreamingEvent,
    EventData,
)


@pytest.mark.unit
class TestStreamingEvent:
    """Test cases for StreamingEvent enum."""

    def test_streaming_events(self):
        """Test streaming event values."""
        assert StreamingEvent.START.value == "streaming.start"
        assert StreamingEvent.CHUNK.value == "streaming.chunk"
        assert StreamingEvent.END.value == "streaming.end"
        assert StreamingEvent.ERROR.value == "streaming.error"

    def test_connection_events(self):
        """Test connection event values."""
        assert StreamingEvent.RESUME.value == "streaming.resume"
        assert StreamingEvent.RECONNECT.value == "streaming.reconnect"
        assert StreamingEvent.DISCONNECT.value == "streaming.disconnect"

    def test_action_events(self):
        """Test action event values."""
        assert StreamingEvent.ACTION_START.value == "action.start"
        assert StreamingEvent.ACTION_COMPLETE.value == "action.complete"
        assert StreamingEvent.OBSERVATION.value == "action.observation"


@pytest.mark.unit
class TestEventData:
    """Test cases for EventData."""

    def test_create_event_data(self):
        """Test creating event data."""
        data = EventData(
            event_type=StreamingEvent.START,
            payload={"message_id": "123"},
        )

        assert data.event_type == StreamingEvent.START
        assert data.payload == {"message_id": "123"}
        assert data.timestamp is not None
        assert data.source is None

    def test_event_data_with_source(self):
        """Test event data with source."""
        data = EventData(
            event_type=StreamingEvent.CHUNK,
            payload={"content": "test"},
            source="agent",
        )

        assert data.source == "agent"


@pytest.mark.unit
class TestEventBus:
    """Test cases for EventBus."""

    def test_init(self):
        """Test EventBus initialization."""
        bus = EventBus()

        assert bus._subscribers == {}
        assert bus._processing is False
        assert len(bus._event_history) == 0

    def test_subscribe(self):
        """Test subscribing to an event."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")

        bus.subscribe(StreamingEvent.START, handler)

        assert StreamingEvent.START in bus._subscribers
        assert len(bus._subscribers[StreamingEvent.START]) == 1

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")

        bus.subscribe(StreamingEvent.START, handler1)
        bus.subscribe(StreamingEvent.START, handler2)

        assert len(bus._subscribers[StreamingEvent.START]) == 2

    def test_subscribe_with_priority(self):
        """Test handler priority ordering."""
        bus = EventBus()
        handler_low = MagicMock(__name__="low")
        handler_high = MagicMock(__name__="high")

        bus.subscribe(StreamingEvent.START, handler_low, priority=1)
        bus.subscribe(StreamingEvent.START, handler_high, priority=10)

        # Higher priority should be first
        handlers = bus._subscribers[StreamingEvent.START]
        assert handlers[0][0] == 10  # priority
        assert handlers[1][0] == 1

    def test_unsubscribe(self):
        """Test unsubscribing from an event."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")

        bus.subscribe(StreamingEvent.START, handler)
        bus.unsubscribe(StreamingEvent.START, handler)

        assert len(bus._subscribers[StreamingEvent.START]) == 0

    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing a nonexistent handler."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")

        # Should not raise
        bus.unsubscribe(StreamingEvent.START, handler)

    @pytest.mark.asyncio
    async def test_emit(self):
        """Test emitting an event."""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe(StreamingEvent.START, handler)
        await bus.emit(StreamingEvent.START, {"message_id": "123"})

        # Wait for event processing
        await asyncio.sleep(0.1)

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args["message_id"] == "123"

    @pytest.mark.asyncio
    async def test_emit_to_multiple_handlers(self):
        """Test emitting to multiple handlers."""
        bus = EventBus()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(StreamingEvent.CHUNK, handler1)
        bus.subscribe(StreamingEvent.CHUNK, handler2)

        await bus.emit(StreamingEvent.CHUNK, {"content": "test"})
        await asyncio.sleep(0.1)

        handler1.assert_called_once()
        handler2.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_sync_handler(self):
        """Test emitting to synchronous handler."""
        bus = EventBus()
        handler = MagicMock(__name__="sync_handler")

        bus.subscribe(StreamingEvent.END, handler)
        await bus.emit(StreamingEvent.END, {"status": "complete"})
        await asyncio.sleep(0.1)

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_adds_to_history(self):
        """Test that emit adds to event history."""
        bus = EventBus()

        await bus.emit(StreamingEvent.START, {"id": "1"})
        await bus.emit(StreamingEvent.CHUNK, {"id": "2"})
        await asyncio.sleep(0.1)

        history = bus.get_history()
        assert len(history) == 2

    def test_get_history(self):
        """Test getting event history."""
        bus = EventBus()

        # Manually add to history
        bus._add_to_history(EventData(event_type=StreamingEvent.START, payload={"id": "1"}))
        bus._add_to_history(EventData(event_type=StreamingEvent.END, payload={"id": "2"}))

        history = bus.get_history()
        assert len(history) == 2

    def test_get_history_filtered(self):
        """Test getting filtered event history."""
        bus = EventBus()

        bus._add_to_history(EventData(event_type=StreamingEvent.START, payload={}))
        bus._add_to_history(EventData(event_type=StreamingEvent.CHUNK, payload={}))
        bus._add_to_history(EventData(event_type=StreamingEvent.END, payload={}))

        history = bus.get_history(event_type=StreamingEvent.CHUNK)
        assert len(history) == 1
        assert history[0].event_type == StreamingEvent.CHUNK

    def test_get_history_with_limit(self):
        """Test getting limited event history."""
        bus = EventBus()

        for i in range(10):
            bus._add_to_history(EventData(event_type=StreamingEvent.CHUNK, payload={"index": i}))

        history = bus.get_history(limit=5)
        assert len(history) == 5
        # Should return last 5
        assert history[-1].payload["index"] == 9

    def test_clear_history(self):
        """Test clearing event history."""
        bus = EventBus()

        bus._add_to_history(EventData(event_type=StreamingEvent.START, payload={}))

        bus.clear_history()
        assert len(bus._event_history) == 0

    def test_get_subscriber_count(self):
        """Test getting subscriber count."""
        bus = EventBus()

        assert bus.get_subscriber_count() == 0
        assert bus.get_subscriber_count(StreamingEvent.START) == 0

        bus.subscribe(StreamingEvent.START, MagicMock(__name__="h1"))
        bus.subscribe(StreamingEvent.START, MagicMock(__name__="h2"))
        bus.subscribe(StreamingEvent.END, MagicMock(__name__="h3"))

        assert bus.get_subscriber_count() == 3
        assert bus.get_subscriber_count(StreamingEvent.START) == 2
        assert bus.get_subscriber_count(StreamingEvent.END) == 1

    @pytest.mark.asyncio
    async def test_wait_for_event(self):
        """Test waiting for an event."""
        bus = EventBus()

        async def emit_later():
            await asyncio.sleep(0.1)
            await bus.emit(StreamingEvent.END, {"status": "done"})

        asyncio.create_task(emit_later())

        result = await bus.wait_for_event(StreamingEvent.END, timeout=1.0)

        assert result is not None
        assert result.event_type == StreamingEvent.END

    @pytest.mark.asyncio
    async def test_wait_for_event_timeout(self):
        """Test wait_for_event timeout."""
        bus = EventBus()

        result = await bus.wait_for_event(StreamingEvent.END, timeout=0.1)

        assert result is None

    def test_reset(self):
        """Test resetting the event bus."""
        bus = EventBus()

        bus.subscribe(StreamingEvent.START, MagicMock(__name__="test_handler"))
        bus._add_to_history(EventData(event_type=StreamingEvent.START, payload={}))

        bus.reset()

        assert bus._subscribers == {}
        assert len(bus._event_history) == 0
        assert bus._processing is False
