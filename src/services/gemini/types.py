from enum import Enum
from typing import Any, TypedDict, Union


class MessageRole(Enum):
    """Conversation message roles following Gemini API conventions.

    - SYSTEM: System-level instructions (prepended to context)
    - USER: User input messages (text, images, etc.)
    - MODEL: Model-generated responses
    - TOOL: Tool/function execution results
    """

    SYSTEM = "system"
    USER = "user"
    MODEL = "model"
    TOOL = "tool"


class ToolCall(TypedDict):
    """Represents a function/tool call requested by the model.

    Attributes:
        id: Unique identifier for this tool call (for result routing)
        name: Name of the function/tool to execute
        arguments: Dictionary of argument name -> value pairs
    """

    id: str
    name: str
    arguments: dict[str, Any]


class Message(TypedDict, total=False):
    """Structured conversation message.

    Attributes:
        role: The role of the message sender
        content: Text content or list of content parts (text, images, etc.)
        tool_calls: List of tool calls if this is a model response requesting tools
        tool_call_id: ID of the tool call this message is responding to (for TOOL role)
        name: Tool name (for TOOL role responses)
    """

    role: MessageRole
    content: Union[str, list]
    tool_calls: list[ToolCall]
    tool_call_id: str
    name: str


class ToolParameter(TypedDict, total=False):
    """JSON Schema parameter definition for a tool.

    Attributes:
        type: JSON Schema type (string, integer, number, boolean, array, object)
        description: Human-readable description of the parameter
        enum: List of allowed values (for constrained parameters)
        items: Schema for array items
        properties: Schema for object properties
        required: List of required property names (for objects)
    """

    type: str
    description: str
    enum: list[str]
    items: dict
    properties: dict
    required: list[str]


class ToolDefinition(TypedDict):
    """Complete tool/function definition for Gemini API.

    Attributes:
        name: Function name (should match registered handler)
        description: Clear description of what the function does
        parameters: JSON Schema object describing function parameters
    """

    name: str
    description: str
    parameters: dict[str, Any]


class GenerationConfig(TypedDict, total=False):
    """Configuration options for content generation.

    Attributes:
        response_mime_type: Expected response format (e.g., "application/json")
        response_json_schema: JSON Schema for structured output validation
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        max_output_tokens: Maximum tokens in response
        thinking_config: Configuration for thinking/reasoning features
    """

    response_mime_type: str
    response_json_schema: dict
    temperature: float
    max_output_tokens: int
    thinking_config: dict
