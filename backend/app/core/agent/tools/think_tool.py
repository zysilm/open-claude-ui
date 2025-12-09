"""Think tool for structured reasoning in the ReAct agent.

Based on Anthropic's research: https://www.anthropic.com/engineering/claude-think-tool

The "think" tool creates a dedicated space for structured thinking during complex tasks.
Unlike extended thinking (which happens before response generation), this tool allows
the agent to stop mid-execution and reason about what to do next.

Key benefits:
- Analyze outputs from previous tool calls before proceeding
- Complex decision-making requiring verification
- Sequential decisions where errors carry high costs
- Working memory for multi-step problems
"""

from typing import List
from app.core.agent.tools.base import Tool, ToolParameter, ToolResult


class ThinkTool(Tool):
    """Tool for structured chain-of-thought reasoning.

    This tool allows the agent to pause and think through complex problems
    before taking action. It does not obtain new information or change any
    state - it simply provides a space for reasoning that gets logged.

    Based on Anthropic's research, this simple technique significantly improves
    agent performance on complex tasks requiring policy compliance, sequential
    decisions, and multi-step reasoning.
    """

    @property
    def name(self) -> str:
        return "think"

    @property
    def description(self) -> str:
        return (
            "Use this tool to think through complex problems step-by-step before taking action. "
            "The think tool does NOT execute anything or obtain new information - it simply logs "
            "your reasoning process.\n\n"
            "WHEN TO USE:\n"
            "- Before making important decisions that are hard to reverse\n"
            "- After receiving tool results to analyze what they mean and plan next steps\n"
            "- When facing complex problems that require breaking down into smaller parts\n"
            "- When you need to verify your understanding before proceeding\n"
            "- When multiple approaches exist and you need to evaluate trade-offs\n"
            "- When debugging - to analyze error messages and form hypotheses\n\n"
            "EXAMPLE THOUGHT PATTERNS:\n"
            "- 'Looking at the error message, the issue seems to be X because Y. I should try Z.'\n"
            "- 'The user wants A. To accomplish this, I need to: 1) do X, 2) do Y, 3) do Z.'\n"
            "- 'The file content shows... This means I should edit line N to change...'\n"
            "- 'I have two options: Option A (pros/cons) vs Option B (pros/cons). I'll choose...'\n\n"
            "Think BEFORE acting, especially for file edits, complex bash commands, or multi-step tasks."
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="thought",
                type="string",
                description=(
                    "Your detailed reasoning. Be specific and structured. "
                    "Include: what you observed, what you concluded, and what you plan to do next."
                ),
                required=True,
            ),
        ]

    async def execute(self, thought: str, **kwargs) -> ToolResult:
        """Record a thought in the reasoning log.

        This tool simply returns the thought back, confirming it was recorded.
        The thought becomes part of the conversation history, serving as
        working memory for the agent.

        Args:
            thought: The reasoning to record

        Returns:
            ToolResult confirming the thought was recorded
        """
        # The thought is simply acknowledged and returned
        # The real value is that it gets added to the conversation history,
        # allowing the agent to reference its reasoning in subsequent steps
        return ToolResult(
            success=True,
            output="Thought recorded. Continue with your plan.",
            metadata={"thought_length": len(thought)},
        )
