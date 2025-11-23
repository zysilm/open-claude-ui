"""Base tool interface and registry for ReAct agent."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Callable
from pydantic import BaseModel, Field, ValidationError
import json


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any | None = None


class ToolDefinition(BaseModel):
    """Tool definition for LLM function calling."""
    name: str
    description: str
    parameters: List[ToolParameter]


class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool
    output: str
    error: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_validation_error: bool = Field(
        default=False,
        description="True if error is from parameter validation (handled internally), False if from execution (user-facing)"
    )


class Tool(ABC):
    """Base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        pass

    @property
    def input_schema(self) -> Optional[Type[BaseModel]]:
        """
        Optional Pydantic schema for parameter validation.

        If provided, parameters will be validated before execution.
        Should include json_schema_extra with examples for better error messages.
        """
        return None

    @property
    def handle_validation_error(self) -> Optional[Callable[[ValidationError], str]]:
        """
        Optional handler for validation errors.

        If provided, will be called when parameter validation fails.
        Should return a helpful error message for the LLM to learn from.
        """
        return None

    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    async def validate_and_execute(self, **kwargs) -> ToolResult:
        """
        Validate parameters with Pydantic schema (if provided) and execute tool.

        This method handles:
        1. Parameter validation using input_schema if provided
        2. Calling validation error handler on validation failures
        3. Providing helpful error messages with schema examples
        4. Executing the tool with validated parameters

        Returns:
            ToolResult with success=False and actionable error message on validation failure
        """
        # If no schema provided, execute directly
        if self.input_schema is None:
            try:
                return await self.execute(**kwargs)
            except Exception as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Tool execution error: {str(e)}"
                )

        # Validate parameters with Pydantic schema
        try:
            validated_input = self.input_schema(**kwargs)
            return await self.execute(**validated_input.model_dump())

        except ValidationError as e:
            # Use custom validation error handler if provided
            if self.handle_validation_error:
                error_message = self.handle_validation_error(e)
            else:
                # Default validation error message
                error_message = self._format_validation_error(e)

            return ToolResult(
                success=False,
                output="",
                error=error_message,
                is_validation_error=True  # Mark as validation error for internal handling
            )

        except Exception as e:
            # Handle execution errors
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution error: {str(e)}"
            )

    def _format_validation_error(self, error: ValidationError) -> str:
        """Format validation error with helpful details."""
        errors = error.errors()
        error_details = "\n".join([
            f"  - {err['loc'][0] if err['loc'] else 'root'}: {err['msg']}"
            for err in errors
        ])

        message = f"Parameter validation failed for '{self.name}':\n{error_details}\n"

        # Add schema information if available
        if self.input_schema:
            schema = self.input_schema.model_json_schema()

            # Add example if available
            if 'examples' in schema and schema['examples']:
                example = schema['examples'][0]
                message += f"\nExample valid call:\n{json.dumps(example, indent=2)}\n"

            # Add required fields
            if 'required' in schema:
                required = ", ".join(schema['required'])
                message += f"\nRequired parameters: {required}\n"

        message += "\nPlease check the parameters and try again."
        return message

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def format_for_llm(self) -> Dict[str, Any]:
        """Format tool definition for LLM function calling (OpenAI format)."""
        parameters_dict = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param in self.parameters:
            parameters_dict["properties"][param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                parameters_dict["properties"][param.name]["default"] = param.default
            if param.required:
                parameters_dict["required"].append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters_dict,
            }
        }


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get(self, tool_name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get all tools formatted for LLM function calling."""
        return [tool.format_for_llm() for tool in self._tools.values()]

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools
