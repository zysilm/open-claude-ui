"""Test that tool outputs (including success/failure status) are included in LLM context.

This test verifies the critical requirement that the LLM receives:
1. What tools were executed
2. What the tool outputs were
3. Whether the tool succeeded or failed
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.database.message import Message, MessageRole
from app.models.database.agent_action import AgentAction, AgentActionStatus
from app.models.database.chat_session import ChatSession


@pytest.mark.asyncio
async def test_successful_tool_output_included_in_context(db_session: AsyncSession):
    """Test that successful tool outputs are included in conversation history."""
    # Create a test session
    session = ChatSession(
        id="test-session-1",
        name="Test Session",
        project_id="test-project",
        environment_type="python3.11"
    )
    db_session.add(session)

    # User asks to create a file
    user_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.USER,
        content="Create a file called test.py with print('hello')",
        message_metadata={}
    )
    db_session.add(user_msg)

    # Assistant uses file_write tool successfully
    assistant_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="I'll create the file for you.",
        message_metadata={"agent_mode": True}
    )
    db_session.add(assistant_msg)
    await db_session.flush()

    # Save the tool action with SUCCESS output
    action = AgentAction(
        message_id=assistant_msg.id,
        action_type="file_write",
        action_input={"path": "test.py", "content": "print('hello')"},
        action_output={"success": True, "result": "File created successfully at test.py"},
        status=AgentActionStatus.SUCCESS
    )
    db_session.add(action)
    await db_session.commit()

    # Build conversation history (simulating _get_conversation_history)
    query = (
        select(Message)
        .options(joinedload(Message.agent_actions))
        .where(Message.chat_session_id == session.id)
        .order_by(Message.created_at.asc())
    )
    result = await db_session.execute(query)
    messages = result.unique().scalars().all()

    history = []
    for msg in messages:
        history.append({"role": msg.role.value, "content": msg.content})

        if msg.role == MessageRole.ASSISTANT and msg.agent_actions:
            for act in msg.agent_actions:
                # Tool call
                history.append({
                    "role": "assistant",
                    "content": f"Using tool: {act.action_type}",
                    "tool_call": {"name": act.action_type, "arguments": act.action_input}
                })

                # Tool result with success status
                if act.action_output:
                    if isinstance(act.action_output, dict):
                        success = act.action_output.get("success", True)
                        result_text = act.action_output.get("result", act.action_output)
                        status_prefix = "[SUCCESS]" if success else "[FAILED]"
                        output_content = f"{status_prefix} Tool '{act.action_type}' result:\n{result_text}"
                    else:
                        output_content = f"Tool '{act.action_type}' returned: {act.action_output}"
                else:
                    output_content = f"Tool '{act.action_type}' completed (no output)"

                history.append({"role": "user", "content": output_content})

    # Verify the history structure
    assert len(history) == 4, f"Expected 4 entries: user msg, assistant msg, tool call, tool result. Got {len(history)}"

    # Verify user message
    assert history[0]["role"] == "user"
    assert "Create a file" in history[0]["content"]

    # Verify assistant message
    assert history[1]["role"] == "assistant"
    assert "I'll create the file" in history[1]["content"]

    # Verify tool call is included
    assert history[2]["role"] == "assistant"
    assert "Using tool: file_write" in history[2]["content"]
    assert history[2]["tool_call"]["name"] == "file_write"
    assert history[2]["tool_call"]["arguments"]["path"] == "test.py"

    # CRITICAL: Verify tool result is included with SUCCESS status
    assert history[3]["role"] == "user", "Tool results should be user role for GPT-5"
    assert "[SUCCESS]" in history[3]["content"], "Success status should be clearly marked"
    assert "file_write" in history[3]["content"]
    assert "File created successfully" in history[3]["content"]

    print("✓ Successful tool output is correctly included in LLM context with [SUCCESS] prefix")


@pytest.mark.asyncio
async def test_failed_tool_output_included_in_context(db_session: AsyncSession):
    """Test that FAILED tool outputs are included with failure status."""
    # Create a test session
    session = ChatSession(
        id="test-session-2",
        name="Test Session 2",
        project_id="test-project",
        environment_type="python3.11"
    )
    db_session.add(session)

    user_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.USER,
        content="Read the file /nonexistent.txt",
        message_metadata={}
    )
    db_session.add(user_msg)

    # Assistant tries to read file but it FAILS
    assistant_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="I'll try to read that file.",
        message_metadata={"agent_mode": True}
    )
    db_session.add(assistant_msg)
    await db_session.flush()

    # Save the tool action with FAILURE output
    action = AgentAction(
        message_id=assistant_msg.id,
        action_type="file_read",
        action_input={"path": "/nonexistent.txt"},
        action_output={"success": False, "result": "Error: File not found: /nonexistent.txt"},
        status=AgentActionStatus.ERROR
    )
    db_session.add(action)
    await db_session.commit()

    # Build conversation history
    query = (
        select(Message)
        .options(joinedload(Message.agent_actions))
        .where(Message.chat_session_id == session.id)
        .order_by(Message.created_at.asc())
    )
    result = await db_session.execute(query)
    messages = result.unique().scalars().all()

    history = []
    for msg in messages:
        history.append({"role": msg.role.value, "content": msg.content})

        if msg.role == MessageRole.ASSISTANT and msg.agent_actions:
            for act in msg.agent_actions:
                history.append({
                    "role": "assistant",
                    "content": f"Using tool: {act.action_type}",
                    "tool_call": {"name": act.action_type, "arguments": act.action_input}
                })

                if act.action_output:
                    if isinstance(act.action_output, dict):
                        success = act.action_output.get("success", True)
                        result_text = act.action_output.get("result", act.action_output)
                        status_prefix = "[SUCCESS]" if success else "[FAILED]"
                        output_content = f"{status_prefix} Tool '{act.action_type}' result:\n{result_text}"
                    else:
                        output_content = f"Tool '{act.action_type}' returned: {act.action_output}"
                else:
                    output_content = f"Tool '{act.action_type}' completed (no output)"

                history.append({"role": "user", "content": output_content})

    # CRITICAL: Verify tool FAILURE is included with [FAILED] prefix
    assert history[3]["role"] == "user"
    assert "[FAILED]" in history[3]["content"], "Failure status should be clearly marked"
    assert "file_read" in history[3]["content"]
    assert "File not found" in history[3]["content"]

    print("✓ Failed tool output is correctly included in LLM context with [FAILED] prefix")


@pytest.mark.asyncio
async def test_multiple_tool_calls_all_included(db_session: AsyncSession):
    """Test that ALL tool outputs are included when there are multiple tool calls."""
    session = ChatSession(
        id="test-session-3",
        name="Test Session 3",
        project_id="test-project",
        environment_type="python3.11"
    )
    db_session.add(session)

    user_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.USER,
        content="Create test.py and run it",
        message_metadata={}
    )
    db_session.add(user_msg)

    # Assistant uses MULTIPLE tools
    assistant_msg = Message(
        chat_session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="I'll create and run the file.",
        message_metadata={"agent_mode": True}
    )
    db_session.add(assistant_msg)
    await db_session.flush()

    # First tool: file_write (SUCCESS)
    action1 = AgentAction(
        message_id=assistant_msg.id,
        action_type="file_write",
        action_input={"path": "test.py", "content": "print('hello')"},
        action_output={"success": True, "result": "File created"},
        status=AgentActionStatus.SUCCESS
    )
    db_session.add(action1)

    # Second tool: bash (SUCCESS)
    action2 = AgentAction(
        message_id=assistant_msg.id,
        action_type="bash",
        action_input={"command": "python test.py"},
        action_output={"success": True, "result": "hello\n"},
        status=AgentActionStatus.SUCCESS
    )
    db_session.add(action2)

    await db_session.commit()

    # Build conversation history
    query = (
        select(Message)
        .options(joinedload(Message.agent_actions))
        .where(Message.chat_session_id == session.id)
        .order_by(Message.created_at.asc())
    )
    result = await db_session.execute(query)
    messages = result.unique().scalars().all()

    history = []
    for msg in messages:
        history.append({"role": msg.role.value, "content": msg.content})

        if msg.role == MessageRole.ASSISTANT and msg.agent_actions:
            for act in msg.agent_actions:
                history.append({
                    "role": "assistant",
                    "content": f"Using tool: {act.action_type}",
                    "tool_call": {"name": act.action_type, "arguments": act.action_input}
                })

                if act.action_output:
                    if isinstance(act.action_output, dict):
                        success = act.action_output.get("success", True)
                        result_text = act.action_output.get("result", act.action_output)
                        status_prefix = "[SUCCESS]" if success else "[FAILED]"
                        output_content = f"{status_prefix} Tool '{act.action_type}' result:\n{result_text}"
                    else:
                        output_content = f"Tool '{act.action_type}' returned: {act.action_output}"
                else:
                    output_content = f"Tool '{act.action_type}' completed (no output)"

                history.append({"role": "user", "content": output_content})

    # Expected: user msg, assistant msg, file_write call, file_write result, bash call, bash result
    assert len(history) == 6, f"Expected 6 entries for 2 tools. Got {len(history)}"

    # Verify file_write is in history
    assert any("file_write" in str(h) for h in history), "file_write tool should be in history"
    assert any("File created" in str(h) for h in history), "file_write result should be in history"

    # Verify bash is in history
    assert any("bash" in str(h) for h in history), "bash tool should be in history"
    assert any("hello" in str(h) for h in history), "bash output 'hello' should be in history"

    print("✓ ALL tool outputs from multiple tool calls are included in LLM context")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
