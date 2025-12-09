"""Tests for ContentBlock Pydantic schemas."""

import pytest
from datetime import datetime

from app.models.schemas.content_block import (
    ContentBlockBase,
    ContentBlockCreate,
    ContentBlockUpdate,
    ContentBlockResponse,
    ContentBlockListResponse,
    TextContent,
    ToolCallContent,
    ToolResultContent,
)
from app.models.database.content_block import ContentBlockType, ContentBlockAuthor


@pytest.mark.unit
class TestContentBlockSchemas:
    """Test cases for ContentBlock schemas."""

    def test_content_block_base_valid(self):
        """Test valid ContentBlockBase schema."""
        block = ContentBlockBase(
            block_type=ContentBlockType.USER_TEXT,
            author=ContentBlockAuthor.USER,
            content={"text": "Hello"},
        )
        assert block.block_type == ContentBlockType.USER_TEXT
        assert block.author == ContentBlockAuthor.USER
        assert block.content == {"text": "Hello"}

    def test_content_block_base_defaults(self):
        """Test ContentBlockBase default values."""
        block = ContentBlockBase(
            block_type=ContentBlockType.ASSISTANT_TEXT,
            author=ContentBlockAuthor.ASSISTANT,
        )
        assert block.content == {}
        assert block.block_metadata == {}

    def test_content_block_create(self):
        """Test ContentBlockCreate schema."""
        block = ContentBlockCreate(
            block_type=ContentBlockType.TOOL_CALL,
            author=ContentBlockAuthor.ASSISTANT,
            content={"tool_name": "bash", "arguments": {}},
            parent_block_id=None,
        )
        assert block.block_type == ContentBlockType.TOOL_CALL
        assert block.parent_block_id is None

    def test_content_block_create_with_parent(self):
        """Test ContentBlockCreate with parent."""
        block = ContentBlockCreate(
            block_type=ContentBlockType.TOOL_RESULT,
            author=ContentBlockAuthor.TOOL,
            content={"result": "success"},
            parent_block_id="parent-block-id",
        )
        assert block.parent_block_id == "parent-block-id"

    def test_content_block_update(self):
        """Test ContentBlockUpdate schema."""
        update = ContentBlockUpdate(
            content={"text": "Updated content"},
        )
        assert update.content == {"text": "Updated content"}
        assert update.block_metadata is None

    def test_content_block_update_metadata(self):
        """Test ContentBlockUpdate with metadata."""
        update = ContentBlockUpdate(
            block_metadata={"streaming": False},
        )
        assert update.content is None
        assert update.block_metadata == {"streaming": False}

    def test_content_block_response(self):
        """Test ContentBlockResponse schema."""
        now = datetime.utcnow()
        response = ContentBlockResponse(
            id="block-id",
            chat_session_id="session-id",
            sequence_number=1,
            block_type=ContentBlockType.USER_TEXT,
            author=ContentBlockAuthor.USER,
            content={"text": "Hello"},
            parent_block_id=None,
            block_metadata={},
            created_at=now,
            updated_at=now,
        )
        assert response.id == "block-id"
        assert response.sequence_number == 1
        assert response.block_type == ContentBlockType.USER_TEXT

    def test_content_block_list_response(self):
        """Test ContentBlockListResponse schema."""
        now = datetime.utcnow()
        blocks = [
            ContentBlockResponse(
                id=f"block-{i}",
                chat_session_id="session-id",
                sequence_number=i,
                block_type=ContentBlockType.USER_TEXT,
                author=ContentBlockAuthor.USER,
                content={"text": f"Message {i}"},
                block_metadata={},
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]
        response = ContentBlockListResponse(blocks=blocks, total=10)

        assert len(response.blocks) == 3
        assert response.total == 10


@pytest.mark.unit
class TestContentTypeSchemas:
    """Test cases for content type helper schemas."""

    def test_text_content(self):
        """Test TextContent schema."""
        content = TextContent(text="Hello, world!")
        assert content.text == "Hello, world!"

    def test_text_content_empty(self):
        """Test TextContent with empty string."""
        content = TextContent(text="")
        assert content.text == ""

    def test_tool_call_content(self):
        """Test ToolCallContent schema."""
        content = ToolCallContent(
            tool_name="bash",
            arguments={"command": "ls -la"},
            status="pending",
        )
        assert content.tool_name == "bash"
        assert content.arguments == {"command": "ls -la"}
        assert content.status == "pending"

    def test_tool_call_content_defaults(self):
        """Test ToolCallContent default values."""
        content = ToolCallContent(tool_name="file_read")
        assert content.arguments == {}
        assert content.status == "pending"

    def test_tool_result_content_success(self):
        """Test ToolResultContent for successful result."""
        content = ToolResultContent(
            tool_name="bash",
            result="file1.py\nfile2.py",
            success=True,
        )
        assert content.tool_name == "bash"
        assert content.result == "file1.py\nfile2.py"
        assert content.success is True
        assert content.error is None

    def test_tool_result_content_error(self):
        """Test ToolResultContent for error result."""
        content = ToolResultContent(
            tool_name="bash",
            result=None,
            success=False,
            error="Command not found",
        )
        assert content.success is False
        assert content.error == "Command not found"

    def test_tool_result_content_binary(self):
        """Test ToolResultContent for binary result."""
        content = ToolResultContent(
            tool_name="file_read",
            result=None,
            success=True,
            is_binary=True,
            binary_type="image/png",
            binary_data="base64encodeddata...",
        )
        assert content.is_binary is True
        assert content.binary_type == "image/png"
        assert content.binary_data == "base64encodeddata..."

    def test_tool_result_content_defaults(self):
        """Test ToolResultContent default values."""
        content = ToolResultContent(tool_name="think")
        assert content.result is None
        assert content.success is True
        assert content.error is None
        assert content.is_binary is False
        assert content.binary_type is None
        assert content.binary_data is None
