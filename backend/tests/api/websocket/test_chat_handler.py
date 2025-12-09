"""Tests for the ChatWebSocketHandler module."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.api.websocket.chat_handler import (
    is_vision_model,
    ToolCallState,
    StreamState,
    ChatWebSocketHandler,
    create_orchestrator,
)
from app.models.database import ContentBlock, ContentBlockType, ContentBlockAuthor


@pytest.mark.websocket
class TestIsVisionModel:
    """Test the is_vision_model helper function."""

    def test_gpt4o_is_vision_model(self):
        """Test that GPT-4o models are recognized as vision models."""
        assert is_vision_model("gpt-4o") is True
        assert is_vision_model("gpt-4o-mini") is True
        assert is_vision_model("GPT-4O") is True

    def test_gpt4_turbo_is_vision_model(self):
        """Test that GPT-4 Turbo is recognized as vision model."""
        assert is_vision_model("gpt-4-turbo") is True
        assert is_vision_model("gpt-4-turbo-preview") is True

    def test_gpt4_vision_is_vision_model(self):
        """Test that GPT-4 Vision is recognized as vision model."""
        assert is_vision_model("gpt-4-vision") is True
        assert is_vision_model("gpt-4-vision-preview") is True

    def test_claude3_is_vision_model(self):
        """Test that Claude 3 models are recognized as vision models."""
        assert is_vision_model("claude-3-opus") is True
        assert is_vision_model("claude-3-sonnet") is True
        assert is_vision_model("claude-3-haiku") is True
        assert is_vision_model("claude-3.5-sonnet") is True

    def test_claude_variants_are_vision_models(self):
        """Test Claude variant names are recognized."""
        assert is_vision_model("claude-sonnet") is True
        assert is_vision_model("claude-opus") is True
        assert is_vision_model("claude-haiku") is True

    def test_gemini_pro_is_vision_model(self):
        """Test Gemini Pro is recognized as vision model."""
        assert is_vision_model("gemini-pro") is True
        assert is_vision_model("gemini-pro-vision") is True

    def test_gpt35_not_vision_model(self):
        """Test that GPT-3.5 is not recognized as vision model."""
        assert is_vision_model("gpt-3.5-turbo") is False
        assert is_vision_model("gpt-3.5") is False

    def test_gpt4_base_not_vision_model(self):
        """Test that base GPT-4 (without turbo/vision) is not vision model."""
        assert is_vision_model("gpt-4") is False

    def test_claude2_not_vision_model(self):
        """Test that Claude 2 is not recognized as vision model."""
        assert is_vision_model("claude-2") is False
        assert is_vision_model("claude-2.1") is False

    def test_unknown_model_not_vision(self):
        """Test that unknown models are not vision models."""
        assert is_vision_model("llama-2") is False
        assert is_vision_model("mistral-7b") is False


@pytest.mark.websocket
class TestToolCallState:
    """Test the ToolCallState dataclass."""

    def test_tool_call_state_defaults(self):
        """Test ToolCallState default values."""
        state = ToolCallState(tool_name="bash")
        assert state.tool_name == "bash"
        assert state.partial_args == ""
        assert state.step == 0
        assert state.status == "streaming"

    def test_tool_call_state_custom_values(self):
        """Test ToolCallState with custom values."""
        state = ToolCallState(
            tool_name="file_read", partial_args='{"path": "/tmp"}', step=5, status="running"
        )
        assert state.tool_name == "file_read"
        assert state.partial_args == '{"path": "/tmp"}'
        assert state.step == 5
        assert state.status == "running"


@pytest.mark.websocket
class TestStreamState:
    """Test the StreamState dataclass."""

    def test_stream_state_defaults(self):
        """Test StreamState default values."""
        state = StreamState(block_id="block-123", session_id="session-456")
        assert state.block_id == "block-123"
        assert state.session_id == "session-456"
        assert state.accumulated_content == ""
        assert state.streaming is True
        assert state.sequence_number == 0
        assert state.active_tool_call is None

    def test_stream_state_with_tool_call(self):
        """Test StreamState with active tool call."""
        tool_state = ToolCallState(tool_name="bash")
        state = StreamState(
            block_id="block-123",
            session_id="session-456",
            accumulated_content="Hello world",
            streaming=False,
            sequence_number=5,
            active_tool_call=tool_state,
        )
        assert state.accumulated_content == "Hello world"
        assert state.streaming is False
        assert state.sequence_number == 5
        assert state.active_tool_call.tool_name == "bash"


@pytest.mark.websocket
class TestChatWebSocketHandler:
    """Test the ChatWebSocketHandler class."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_handler_init(self, mock_websocket, mock_db_session):
        """Test handler initialization."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)
        assert handler.websocket == mock_websocket
        assert handler.db == mock_db_session
        assert handler.current_agent_task is None
        assert handler.cancel_event is None
        assert handler._sequence_cache == {}

    @pytest.mark.asyncio
    async def test_safe_commit(self, mock_websocket, mock_db_session):
        """Test safe commit uses lock."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Call _safe_commit
        await handler._safe_commit()

        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_block_to_dict(self, mock_websocket, mock_db_session):
        """Test converting ContentBlock to dict."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Create a mock ContentBlock
        block = MagicMock(spec=ContentBlock)
        block.id = "block-123"
        block.chat_session_id = "session-456"
        block.sequence_number = 1
        block.block_type = ContentBlockType.USER_TEXT
        block.author = ContentBlockAuthor.USER
        block.content = {"text": "Hello"}
        block.parent_block_id = None
        block.block_metadata = {}
        block.created_at = datetime(2024, 1, 1, 12, 0, 0)
        block.updated_at = None

        result = handler._block_to_dict(block)

        assert result["id"] == "block-123"
        assert result["chat_session_id"] == "session-456"
        assert result["sequence_number"] == 1
        assert result["block_type"] == "user_text"
        assert result["author"] == "user"
        assert result["content"] == {"text": "Hello"}
        assert result["parent_block_id"] is None
        assert result["block_metadata"] == {}
        assert result["created_at"] == "2024-01-01T12:00:00"
        assert result["updated_at"] is None


@pytest.mark.websocket
class TestChatWebSocketHandlerSequencing:
    """Test sequence number management."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_next_sequence_number_empty_session(self, mock_websocket, mock_db_session):
        """Test getting sequence number for empty session."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Mock database returning None (no existing blocks)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        seq = await handler._get_next_sequence_number("session-123")

        assert seq == 1
        assert handler._sequence_cache["session-123"] == 1

    @pytest.mark.asyncio
    async def test_get_next_sequence_number_existing_blocks(self, mock_websocket, mock_db_session):
        """Test getting sequence number with existing blocks."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Mock database returning max sequence 5
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 5
        mock_db_session.execute.return_value = mock_result

        seq = await handler._get_next_sequence_number("session-123")

        assert seq == 6

    @pytest.mark.asyncio
    async def test_get_next_sequence_number_increments(self, mock_websocket, mock_db_session):
        """Test that sequence number increments properly."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Pre-populate cache
        handler._sequence_cache["session-123"] = 5

        seq1 = await handler._get_next_sequence_number("session-123")
        seq2 = await handler._get_next_sequence_number("session-123")
        seq3 = await handler._get_next_sequence_number("session-123")

        assert seq1 == 6
        assert seq2 == 7
        assert seq3 == 8

    @pytest.mark.asyncio
    async def test_get_next_sequence_number_caching(self, mock_websocket, mock_db_session):
        """Test that sequence numbers are cached (no extra DB queries)."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        # Mock database returning max sequence 0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db_session.execute.return_value = mock_result

        # First call - should query DB
        await handler._get_next_sequence_number("session-123")
        assert mock_db_session.execute.call_count == 1

        # Subsequent calls - should use cache
        await handler._get_next_sequence_number("session-123")
        await handler._get_next_sequence_number("session-123")
        assert mock_db_session.execute.call_count == 1  # Still 1


@pytest.mark.websocket
class TestCreateOrchestrator:
    """Test the create_orchestrator factory function."""

    @pytest.mark.asyncio
    async def test_create_orchestrator_returns_orchestrator(self):
        """Test that create_orchestrator returns a MessageOrchestrator."""
        mock_db = MagicMock()

        orchestrator = create_orchestrator(mock_db)

        from app.services.message_orchestrator import MessageOrchestrator

        assert isinstance(orchestrator, MessageOrchestrator)

    @pytest.mark.asyncio
    async def test_create_orchestrator_creates_new_instance(self):
        """Test that create_orchestrator creates new instances each call."""
        mock_db1 = MagicMock()
        mock_db2 = MagicMock()

        orchestrator1 = create_orchestrator(mock_db1)
        orchestrator2 = create_orchestrator(mock_db2)

        # Should be different instances
        assert orchestrator1 is not orchestrator2


@pytest.mark.websocket
class TestChatWebSocketHandlerConcurrency:
    """Test concurrent access to ChatWebSocketHandler."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session with delay."""
        session = MagicMock()

        async def slow_commit():
            await asyncio.sleep(0.01)

        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock(side_effect=slow_commit)
        return session

    @pytest.mark.asyncio
    async def test_concurrent_safe_commits(self, mock_websocket, mock_db_session):
        """Test that concurrent safe_commits don't interleave."""
        handler = ChatWebSocketHandler(mock_websocket, mock_db_session)

        call_order = []

        original_commit = mock_db_session.commit.side_effect

        async def tracked_commit():
            call_order.append("start")
            await original_commit()
            call_order.append("end")

        mock_db_session.commit = AsyncMock(side_effect=tracked_commit)

        # Run multiple commits concurrently
        await asyncio.gather(
            handler._safe_commit(),
            handler._safe_commit(),
            handler._safe_commit(),
        )

        # Due to lock, commits should not interleave
        # Should see: start, end, start, end, start, end
        assert call_order == ["start", "end", "start", "end", "start", "end"]
