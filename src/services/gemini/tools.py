import inspect
import json
import logging
from typing import Any, Callable, Optional, get_args, get_type_hints

from services.gemini.types import ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)


PYTHON_TO_JSON_SCHEMA = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


class ToolValidationError(Exception):
    """Raised when tool argument validation fails."""

    def __init__(self, tool_name: str, message: str, invalid_args: Optional[dict] = None):
        self.tool_name = tool_name
        self.invalid_args = invalid_args or {}
        super().__init__(f"Validation error for tool '{tool_name}': {message}")


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Execution error for tool '{tool_name}': {message}")


class ToolRegistry:
    """Registry for tools/functions available to Gemini.

    Handles:
    - Registration of Python functions as tools
    - Automatic JSON Schema generation from type hints
    - Argument validation before execution
    - Error handling and result formatting

    Example:
        registry = ToolRegistry()

        @registry.tool("Click on a UI element by its ID")
        def click(element_id: int) -> str:
            return f"Clicked element {element_id}"

        # Or register explicitly:
        registry.register(my_function, "Description of what it does")
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, dict] = {}

    def register(
        self,
        func: Callable,
        description: str,
        name: Optional[str] = None,
        parameter_overrides: Optional[dict[str, dict]] = None,
    ) -> None:
        """Register a function as a tool.

        Args:
            func: The Python function to register
            description: Human-readable description of what the tool does
            name: Optional override for the tool name (defaults to function name)
            parameter_overrides: Optional dict of param_name -> schema overrides
        """
        tool_name = name or func.__name__

        schema = self._generate_schema(func, parameter_overrides)

        self._tools[tool_name] = {
            "func": func,
            "description": description,
            "schema": schema,
        }

        logger.debug(f"Registered tool: {tool_name}")

    def tool(self, description: str, name: Optional[str] = None) -> Callable:
        """Decorator to register a function as a tool.

        Args:
            description: Human-readable description of what the tool does
            name: Optional override for the tool name

        Returns:
            Decorator function

        Example:
            @registry.tool("Search the web for information")
            def search_web(query: str) -> str:
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.register(func, description, name)
            return func

        return decorator

    def _generate_schema(
        self,
        func: Callable,
        parameter_overrides: Optional[dict[str, dict]] = None,
    ) -> dict:
        """Generate JSON Schema for a function's parameters.

        Args:
            func: The function to generate schema for
            parameter_overrides: Optional parameter-level schema overrides

        Returns:
            JSON Schema dict describing the function's parameters
        """
        overrides = parameter_overrides or {}

        sig = inspect.signature(func)
        hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name, str)

            origin = getattr(param_type, "__origin__", None)
            if origin is type(None):
                continue

            param_schema: ToolParameter = {}

            if origin is list:
                param_schema["type"] = "array"
                item_type = get_args(param_type)
                if item_type:
                    item_schema_type = PYTHON_TO_JSON_SCHEMA.get(item_type[0], "object")
                else:
                    item_schema_type = "object"
                param_schema["items"] = {"type": item_schema_type}
            elif origin is dict:
                param_schema["type"] = "object"
            else:
                json_type = PYTHON_TO_JSON_SCHEMA.get(param_type, "string")
                param_schema["type"] = json_type

            param_schema["description"] = f"Parameter: {param_name}"

            if param_name in overrides:
                param_schema.update(overrides[param_name])

            properties[param_name] = param_schema

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Get all tool definitions in Gemini-compatible format.

        Returns:
            List of tool definitions ready for the API
        """
        definitions = []

        for name, tool_info in self._tools.items():
            definition: ToolDefinition = {
                "name": name,
                "description": tool_info["description"],
                "parameters": tool_info["schema"],
            }
            definitions.append(definition)

        return definitions

    def validate_args(self, tool_name: str, args: dict) -> dict:
        """Validate arguments against the tool's schema.

        Args:
            tool_name: Name of the tool to validate for
            args: Arguments to validate

        Returns:
            Validated and possibly coerced arguments

        Raises:
            ToolValidationError: If validation fails
        """
        if tool_name not in self._tools:
            raise ToolValidationError(tool_name, f"Unknown tool: {tool_name}")

        schema = self._tools[tool_name]["schema"]
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        validated = {}
        invalid = {}

        for req_param in required:
            if req_param not in args:
                invalid[req_param] = "Required parameter missing"

        for arg_name, arg_value in args.items():
            if arg_name not in properties:
                logger.warning(f"Tool {tool_name}: unexpected argument '{arg_name}'")
                validated[arg_name] = arg_value
                continue

            expected_type = properties[arg_name].get("type", "string")

            try:
                validated[arg_name] = self._coerce_type(arg_value, expected_type)
            except (ValueError, TypeError) as e:
                invalid[arg_name] = f"Type error: expected {expected_type}, got {type(arg_value).__name__}"

        if invalid:
            raise ToolValidationError(tool_name, f"Invalid arguments: {invalid}", invalid)

        return validated

    def _coerce_type(self, value: Any, expected_type: str) -> Any:
        """Attempt to coerce a value to the expected type.

        Args:
            value: Value to coerce
            expected_type: JSON Schema type string

        Returns:
            Coerced value

        Raises:
            ValueError: If coercion fails
        """
        if expected_type == "string":
            return str(value)
        elif expected_type == "integer":
            return int(value)
        elif expected_type == "number":
            return float(value)
        elif expected_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif expected_type == "array":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return json.loads(value)
            return list(value)
        elif expected_type == "object":
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return json.loads(value)
            raise ValueError(f"Cannot coerce {type(value)} to object")
        else:
            return value

    def execute(self, tool_name: str, args: dict) -> Any:
        """Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool

        Returns:
            Result of the tool execution

        Raises:
            ToolValidationError: If argument validation fails
            ToolExecutionError: If tool execution fails
        """
        if tool_name not in self._tools:
            raise ToolValidationError(tool_name, f"Unknown tool: {tool_name}")

        validated_args = self.validate_args(tool_name, args)

        func = self._tools[tool_name]["func"]

        try:
            result = func(**validated_args)
            logger.debug(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise ToolExecutionError(tool_name, str(e), e)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: Name to check

        Returns:
            True if tool is registered
        """
        return tool_name in self._tools

    def list_tools(self) -> list[str]:
        """Get list of registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ToolRegistry({len(self._tools)} tools: {', '.join(self._tools.keys())})"
