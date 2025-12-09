"""Tests for ContentBlock database model."""

import pytest
from sqlalchemy import select

from app.models.database import ContentBlock
from app.models.database.content_block import ContentBlockType, ContentBlockAuthor


@pytest.mark.unit
class TestContentBlockModel:
    """Test cases for the ContentBlock model."""

    @pytest.mark.asyncio
    async def test_create_content_block(self, db_session, sample_chat_session):
        """Test creating a new content block."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.USER_TEXT,
            author=ContentBlockAuthor.USER,
            content={"text": "Hello, world!"},
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        assert block.id is not None
        assert len(block.id) == 36
        assert block.chat_session_id == sample_chat_session.id
        assert block.sequence_number == 1
        assert block.block_type == ContentBlockType.USER_TEXT
        assert block.author == ContentBlockAuthor.USER
        assert block.content == {"text": "Hello, world!"}

    @pytest.mark.asyncio
    async def test_content_block_types(self, db_session, sample_chat_session):
        """Test all ContentBlockType enum values."""
        types_to_test = [
            (ContentBlockType.USER_TEXT, ContentBlockAuthor.USER),
            (ContentBlockType.ASSISTANT_TEXT, ContentBlockAuthor.ASSISTANT),
            (ContentBlockType.TOOL_CALL, ContentBlockAuthor.ASSISTANT),
            (ContentBlockType.TOOL_RESULT, ContentBlockAuthor.TOOL),
            (ContentBlockType.SYSTEM, ContentBlockAuthor.SYSTEM),
        ]

        for i, (block_type, author) in enumerate(types_to_test):
            block = ContentBlock(
                chat_session_id=sample_chat_session.id,
                sequence_number=i + 1,
                block_type=block_type,
                author=author,
                content={"text": f"Block type: {block_type.value}"},
            )
            db_session.add(block)

        await db_session.commit()

        query = (
            select(ContentBlock)
            .where(ContentBlock.chat_session_id == sample_chat_session.id)
            .order_by(ContentBlock.sequence_number)
        )
        result = await db_session.execute(query)
        blocks = result.scalars().all()

        assert len(blocks) == 5

    @pytest.mark.asyncio
    async def test_tool_call_content(self, db_session, sample_chat_session):
        """Test tool_call content structure."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.TOOL_CALL,
            author=ContentBlockAuthor.ASSISTANT,
            content={
                "tool_name": "bash",
                "arguments": {"command": "ls -la", "timeout": 30},
                "status": "pending",
            },
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        assert block.content["tool_name"] == "bash"
        assert block.content["arguments"]["command"] == "ls -la"
        assert block.content["status"] == "pending"

    @pytest.mark.asyncio
    async def test_tool_result_content(self, db_session, sample_chat_session):
        """Test tool_result content structure."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.TOOL_RESULT,
            author=ContentBlockAuthor.TOOL,
            content={
                "tool_name": "bash",
                "result": "file1.py\nfile2.py",
                "success": True,
                "error": None,
            },
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        assert block.content["success"] is True
        assert block.content["result"] == "file1.py\nfile2.py"
        assert block.content["error"] is None

    @pytest.mark.asyncio
    async def test_parent_child_relationship(self, db_session, sample_chat_session):
        """Test parent-child relationship between content blocks."""
        # Create tool call block (parent)
        tool_call = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.TOOL_CALL,
            author=ContentBlockAuthor.ASSISTANT,
            content={"tool_name": "bash", "arguments": {}, "status": "complete"},
        )
        db_session.add(tool_call)
        await db_session.commit()
        await db_session.refresh(tool_call)

        # Create tool result block (child)
        tool_result = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=2,
            block_type=ContentBlockType.TOOL_RESULT,
            author=ContentBlockAuthor.TOOL,
            content={"tool_name": "bash", "result": "success", "success": True},
            parent_block_id=tool_call.id,
        )
        db_session.add(tool_result)
        await db_session.commit()
        await db_session.refresh(tool_result)

        assert tool_result.parent_block_id == tool_call.id

    @pytest.mark.asyncio
    async def test_block_metadata(self, db_session, sample_chat_session):
        """Test block_metadata field."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.ASSISTANT_TEXT,
            author=ContentBlockAuthor.ASSISTANT,
            content={"text": "Response"},
            block_metadata={"streaming": True, "tokens_used": 150},
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        assert block.block_metadata["streaming"] is True
        assert block.block_metadata["tokens_used"] == 150

    @pytest.mark.asyncio
    async def test_content_block_ordering(self, db_session, sample_chat_session):
        """Test content blocks maintain ordering by sequence_number."""
        blocks = [
            ContentBlock(
                chat_session_id=sample_chat_session.id,
                sequence_number=i,
                block_type=ContentBlockType.USER_TEXT,
                author=ContentBlockAuthor.USER,
                content={"text": f"Message {i}"},
            )
            for i in [3, 1, 2]  # Create out of order
        ]
        db_session.add_all(blocks)
        await db_session.commit()

        query = (
            select(ContentBlock)
            .where(ContentBlock.chat_session_id == sample_chat_session.id)
            .order_by(ContentBlock.sequence_number)
        )
        result = await db_session.execute(query)
        ordered_blocks = result.scalars().all()

        assert [b.sequence_number for b in ordered_blocks] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_content_block_repr(self, db_session, sample_chat_session):
        """Test ContentBlock __repr__ method."""
        block = ContentBlock(
            chat_session_id=sample_chat_session.id,
            sequence_number=1,
            block_type=ContentBlockType.USER_TEXT,
            author=ContentBlockAuthor.USER,
            content={"text": "Test"},
        )
        db_session.add(block)
        await db_session.commit()
        await db_session.refresh(block)

        repr_str = repr(block)
        assert "ContentBlock" in repr_str
        assert "user_text" in repr_str
        assert "seq=1" in repr_str

    @pytest.mark.asyncio
    async def test_enum_values(self):
        """Test enum value strings."""
        assert ContentBlockType.USER_TEXT.value == "user_text"
        assert ContentBlockType.ASSISTANT_TEXT.value == "assistant_text"
        assert ContentBlockType.TOOL_CALL.value == "tool_call"
        assert ContentBlockType.TOOL_RESULT.value == "tool_result"
        assert ContentBlockType.SYSTEM.value == "system"

        assert ContentBlockAuthor.USER.value == "user"
        assert ContentBlockAuthor.ASSISTANT.value == "assistant"
        assert ContentBlockAuthor.SYSTEM.value == "system"
        assert ContentBlockAuthor.TOOL.value == "tool"
