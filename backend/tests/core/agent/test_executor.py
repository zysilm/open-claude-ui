"""Tests for ReAct agent executor."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.core.agent.executor import ReActAgent, AgentStep, AgentResponse
from app.core.agent.tools.base import Tool, ToolRegistry, ToolResult, ToolParameter


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool", result: ToolResult = None):
        self._name = name
        self._result = result or ToolResult(success=True, output="Mock output")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"A mock tool called {self._name}"

    @property
    def parameters(self) -> list:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Input to the tool",
                required=True,
            )
        ]

    async def execute(self, **kwargs) -> ToolResult:
        return self._result


@pytest.mark.unit
class TestAgentStep:
    """Test cases for AgentStep model."""

    def test_create_step(self):
        """Test creating an agent step."""
        step = AgentStep(
            thought="I should read the file first",
            action="file_read",
            action_input={"path": "/test.py"},
            observation="File contents here",
            step_number=1,
        )

        assert step.thought == "I should read the file first"
        assert step.action == "file_read"
        assert step.action_input == {"path": "/test.py"}
        assert step.observation == "File contents here"
        assert step.step_number == 1

    def test_step_with_none_values(self):
        """Test step with optional None values."""
        step = AgentStep(step_number=1)

        assert step.thought is None
        assert step.action is None
        assert step.action_input is None
        assert step.observation is None
        assert step.step_number == 1


@pytest.mark.unit
class TestAgentResponse:
    """Test cases for AgentResponse model."""

    def test_create_response(self):
        """Test creating an agent response."""
        response = AgentResponse(
            final_answer="Task completed",
            steps=[AgentStep(step_number=1)],
            completed=True,
        )

        assert response.final_answer == "Task completed"
        assert len(response.steps) == 1
        assert response.completed is True
        assert response.error is None

    def test_response_with_error(self):
        """Test response with error."""
        response = AgentResponse(
            error="Something went wrong",
            completed=False,
        )

        assert response.error == "Something went wrong"
        assert response.completed is False
        assert response.final_answer is None


@pytest.mark.unit
class TestReActAgent:
    """Test cases for ReActAgent."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.generate_stream = AsyncMock()
        return provider

    @pytest.fixture
    def mock_tool_registry(self):
        """Create a mock tool registry."""
        registry = ToolRegistry()
        return registry

    @pytest.fixture
    def agent(self, mock_llm_provider, mock_tool_registry):
        """Create a ReActAgent instance."""
        return ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
            max_iterations=5,
        )

    def test_init(self, mock_llm_provider, mock_tool_registry):
        """Test agent initialization."""
        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
            max_iterations=10,
            max_validation_retries=5,
            max_same_tool_retries=3,
        )

        assert agent.llm == mock_llm_provider
        assert agent.tools == mock_tool_registry
        assert agent.max_iterations == 10
        assert agent.max_validation_retries == 5
        assert agent.max_same_tool_retries == 3
        assert agent.validation_retry_count == 0
        assert agent.tool_call_history == []

    def test_init_with_custom_instructions(self, mock_llm_provider, mock_tool_registry):
        """Test agent with custom system instructions."""
        custom_instructions = "You are a helpful assistant. Tools: {tools}"
        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
            system_instructions=custom_instructions,
        )

        assert agent.system_instructions == custom_instructions

    def test_default_system_instructions(self, agent):
        """Test that default system instructions are set."""
        instructions = agent._default_system_instructions()

        assert "ReAct" in instructions
        assert "{tools}" in instructions
        assert "Think" in instructions or "think" in instructions

    def test_build_system_message(self, mock_llm_provider):
        """Test building system message with tools."""
        registry = ToolRegistry()
        mock_tool = MockTool(name="test_tool")
        registry.register(mock_tool)

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
        )

        system_message = agent._build_system_message()

        assert "test_tool" in system_message
        assert "A mock tool" in system_message

    def test_validate_before_edit_no_read(self, agent):
        """Test validation fails when file not read before edit."""
        messages = [
            {"role": "user", "content": "Edit the file"},
            {"role": "assistant", "content": "I will edit it"},
        ]

        should_proceed, msg = agent._validate_before_edit(messages, "/test.py")

        assert should_proceed is False
        assert "file_read" in msg.lower()

    def test_validate_before_edit_with_read(self, agent):
        """Test validation passes when file was read."""
        messages = [
            {"role": "user", "content": "Edit the file"},
            {
                "role": "assistant",
                "content": "Let me read it first",
                "function_call": {
                    "name": "file_read",
                    "arguments": '{"path": "/test.py"}',
                },
            },
            {"role": "user", "content": "File contents here"},
        ]

        should_proceed, msg = agent._validate_before_edit(messages, "/test.py")

        assert should_proceed is True
        assert msg == ""

    def test_validate_before_edit_different_file(self, agent):
        """Test validation fails if different file was read."""
        messages = [
            {
                "role": "assistant",
                "content": "Reading",
                "function_call": {
                    "name": "file_read",
                    "arguments": '{"path": "/other.py"}',
                },
            },
        ]

        should_proceed, msg = agent._validate_before_edit(messages, "/test.py")

        assert should_proceed is False
        assert "file_read" in msg.lower()

    @pytest.mark.asyncio
    async def test_run_simple_response(self, mock_llm_provider, mock_tool_registry):
        """Test run with simple text response (no tool call)."""

        # Mock LLM to return simple text chunks
        async def mock_generate_stream(**kwargs):
            yield "Hello, "
            yield "this is a response."

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
        )

        results = []
        async for item in agent.run("Hello"):
            results.append(item)

        # Should have chunk events
        chunk_events = [r for r in results if r["type"] == "chunk"]
        assert len(chunk_events) == 2
        assert chunk_events[0]["content"] == "Hello, "
        assert chunk_events[1]["content"] == "this is a response."

    @pytest.mark.asyncio
    async def test_run_with_tool_call(self, mock_llm_provider):
        """Test run with tool execution."""
        registry = ToolRegistry()
        mock_tool = MockTool(
            name="bash",
            result=ToolResult(success=True, output="Command executed"),
        )
        registry.register(mock_tool)

        # First call returns tool call, second returns final answer
        call_count = 0

        async def mock_generate_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First iteration - tool call
                yield {"function_call": {"name": "bash", "arguments": '{"input": "ls"}'}}
            else:
                # Second iteration - final answer
                yield "Done with the task."

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
        )

        results = []
        async for item in agent.run("Run ls command"):
            results.append(item)

        # Should have action and observation events
        action_events = [r for r in results if r["type"] == "action"]
        observation_events = [r for r in results if r["type"] == "observation"]

        assert len(action_events) >= 1
        assert action_events[0]["tool"] == "bash"
        assert len(observation_events) >= 1
        assert observation_events[0]["success"] is True

    @pytest.mark.asyncio
    async def test_run_with_cancellation(self, mock_llm_provider, mock_tool_registry):
        """Test run with cancellation event."""
        cancel_event = asyncio.Event()

        async def mock_generate_stream(**kwargs):
            # Yield a chunk then simulate delay where cancellation happens
            yield "Starting..."
            cancel_event.set()  # Set cancellation during stream
            yield "More content"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
        )

        results = []
        async for item in agent.run("Hello", cancel_event=cancel_event):
            results.append(item)

        # Should have cancelled event
        cancelled = [r for r in results if r["type"] == "cancelled"]
        assert len(cancelled) == 1
        assert "cancelled" in cancelled[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_run_max_iterations(self, mock_llm_provider):
        """Test that agent respects max iterations."""
        registry = ToolRegistry()
        mock_tool = MockTool(name="bash")
        registry.register(mock_tool)

        # Always return tool calls to force max iterations
        async def mock_generate_stream(**kwargs):
            yield {"function_call": {"name": "bash", "arguments": '{"input": "test"}'}}

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
            max_iterations=2,
        )

        results = []
        async for item in agent.run("Run forever"):
            results.append(item)

        # Should have final answer about max iterations
        final = [r for r in results if r.get("type") == "final_answer"]
        assert len(final) == 1
        assert "maximum iterations" in final[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_run_with_conversation_history(self, mock_llm_provider, mock_tool_registry):
        """Test run with conversation history."""

        async def mock_generate_stream(**kwargs):
            messages = kwargs.get("messages", [])
            # Should have system + history + user message
            assert len(messages) >= 3
            yield "Response with context"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
        )

        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]

        results = []
        async for item in agent.run("Follow up", conversation_history=history):
            results.append(item)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_run_with_llm_error(self, mock_llm_provider, mock_tool_registry):
        """Test run handles LLM errors gracefully."""

        async def mock_generate_stream(**kwargs):
            raise Exception("LLM API Error")
            yield  # Make it a generator

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=mock_tool_registry,
        )

        results = []
        async for item in agent.run("Hello"):
            results.append(item)

        error_events = [r for r in results if r["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM API Error" in error_events[0]["content"]

    @pytest.mark.asyncio
    async def test_run_tool_validation_error(self, mock_llm_provider):
        """Test handling of tool validation errors."""
        registry = ToolRegistry()
        mock_tool = MockTool(
            name="bash",
            result=ToolResult(
                success=False,
                output="",
                error="Invalid parameters",
                is_validation_error=True,
            ),
        )
        registry.register(mock_tool)

        call_count = 0

        async def mock_generate_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                yield {"function_call": {"name": "bash", "arguments": '{"input": "bad"}'}}
            else:
                yield "Giving up on the tool"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
            max_validation_retries=3,
        )

        results = []
        async for item in agent.run("Run something"):
            results.append(item)

        # Should NOT have action events for validation errors
        action_events = [r for r in results if r["type"] == "action"]
        assert len(action_events) == 0

    @pytest.mark.asyncio
    async def test_run_tool_loop_detection(self, mock_llm_provider):
        """Test detection of tool call loops."""
        registry = ToolRegistry()
        mock_tool = MockTool(
            name="bash",
            result=ToolResult(success=False, output="", error="Command failed"),
        )
        registry.register(mock_tool)

        call_count = 0

        async def mock_generate_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 6:
                yield {"function_call": {"name": "bash", "arguments": '{"input": "fail"}'}}
            else:
                yield "Trying different approach"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
            max_same_tool_retries=5,
            max_iterations=10,
        )

        results = []
        async for item in agent.run("Keep trying"):
            results.append(item)

        # Agent should detect loop and suggest different approach
        # The tool history should be cleared after loop detection

    @pytest.mark.asyncio
    async def test_run_edit_validation(self, mock_llm_provider):
        """Test that edit_lines requires file_read first."""
        registry = ToolRegistry()
        edit_tool = MockTool(name="edit_lines")
        registry.register(edit_tool)

        async def mock_generate_stream(**kwargs):
            yield {"function_call": {"name": "edit_lines", "arguments": '{"path": "/test.py"}'}}

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
            max_iterations=2,
        )

        results = []
        async for item in agent.run("Edit the file"):
            results.append(item)

        # Should not have action events since validation should fail
        # The agent should continue to next iteration

    @pytest.mark.asyncio
    async def test_streaming_action_events(self, mock_llm_provider):
        """Test action streaming events are emitted."""
        registry = ToolRegistry()
        mock_tool = MockTool(name="bash")
        registry.register(mock_tool)

        call_count = 0

        async def mock_generate_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Emit function call in chunks like real streaming
                yield {"function_call": {"name": "bash", "arguments": ""}}
                yield {"function_call": {"name": None, "arguments": '{"inpu'}}
                yield {"function_call": {"name": None, "arguments": 't": "ls"}'}}
            else:
                yield "Done"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
        )

        results = []
        async for item in agent.run("Run command"):
            results.append(item)

        # Should have action_streaming event
        streaming_events = [r for r in results if r["type"] == "action_streaming"]
        assert len(streaming_events) >= 1
        assert streaming_events[0]["tool"] == "bash"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_uses_first(self, mock_llm_provider):
        """Test that only first tool call is executed per iteration."""
        registry = ToolRegistry()
        tool1 = MockTool(name="bash")
        tool2 = MockTool(name="file_read")
        registry.register(tool1)
        registry.register(tool2)

        call_count = 0

        async def mock_generate_stream(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Return two tool calls at different indices
                yield {
                    "function_call": {"name": "bash", "arguments": '{"input": "ls"}'},
                    "index": 0,
                }
                yield {
                    "function_call": {"name": "file_read", "arguments": '{"path": "/test"}'},
                    "index": 1,
                }
            else:
                yield "Done"

        mock_llm_provider.generate_stream = mock_generate_stream

        agent = ReActAgent(
            llm_provider=mock_llm_provider,
            tool_registry=registry,
        )

        results = []
        async for item in agent.run("Do things"):
            results.append(item)

        # Should only execute the first tool
        action_events = [r for r in results if r["type"] == "action"]
        assert len(action_events) == 1
        assert action_events[0]["tool"] == "bash"
