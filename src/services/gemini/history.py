import logging
from typing import Any, Optional
from services.gemini.types import Message, MessageRole, ToolCall

logger = logging.getLogger(__name__)


class ConversationHistory:
    """Manages conversation history with structured message storage.

    Features:
    - Role-based message tracking (user, model, tool)
    - Configurable truncation strategies
    - Optional summarization using Gemini
    - API-compatible message formatting

    The history is model-agnostic internally but provides Gemini-specific
    formatting through get_messages_for_api().
    """

    def __init__(
        self,
        max_messages: int = 20,
        max_tokens: int = 50000,
        truncation_strategy: str = "oldest_first",
    ):
        """Initialize conversation history.

        Args:
            max_messages: Maximum number of messages to retain
            max_tokens: Approximate token limit (used for summarization triggers)
            truncation_strategy: How to truncate - "oldest_first" or "importance_based"
        """
        self.messages: list[Message] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.truncation_strategy = truncation_strategy
        self._system_instruction: Optional[str] = None

    def set_system_instruction(self, instruction: str) -> None:
        """Set the system instruction (prepended to all API calls).

        Args:
            instruction: System-level instruction for the model
        """
        self._system_instruction = instruction

    def add_user_message(self, content: str | list) -> None:
        """Add a user message to history.

        Args:
            content: Text string or list of content parts (text, images, etc.)
        """
        message: Message = {
            "role": MessageRole.USER,
            "content": content,
        }
        self.messages.append(message)
        self._maybe_truncate()

    def add_model_response(self, content: str | list, tool_calls: Optional[list[ToolCall]] = None) -> None:
        """Add a model response to history.

        Args:
            content: Model's text response or list of parts
            tool_calls: Optional list of tool calls the model requested
        """
        message: Message = {
            "role": MessageRole.MODEL,
            "content": content,
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.messages.append(message)
        self._maybe_truncate()

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: Any) -> None:
        """Add a tool execution result to history.

        Args:
            tool_call_id: ID of the tool call being responded to
            tool_name: Name of the tool that was executed
            result: Result of the tool execution (will be converted to string)
        """
        message: Message = {
            "role": MessageRole.TOOL,
            "content": str(result),
            "tool_call_id": tool_call_id,
            "name": tool_name,
        }
        self.messages.append(message)

    def add_raw_content(self, role: str, content: Any) -> None:
        """Add raw Gemini API content directly (for compatibility with existing code).

        This is a bridge method for migrating existing code that passes
        Gemini Content objects directly.

        Args:
            role: Role string ("user" or "model")
            content: Raw content (Gemini Content object or dict)
        """
        message_role = MessageRole.USER if role == "user" else MessageRole.MODEL
        message: Message = {
            "role": message_role,
            "content": content,
        }
        self.messages.append(message)
        self._maybe_truncate()

    def get_messages_for_api(self) -> list[dict]:
        """Get messages formatted for Gemini API.

        Returns:
            List of dicts with 'role' and 'parts' keys compatible with Gemini API
        """
        api_messages = []

        for msg in self.messages:
            role = msg["role"]
            content = msg.get("content", "")

            if role == MessageRole.USER:
                api_role = "user"
            elif role == MessageRole.MODEL:
                api_role = "model"
            elif role == MessageRole.TOOL:
                api_role = "user"
            else:
                api_role = "user"

            if isinstance(content, str):
                parts = [{"text": content}] if content else []
            elif isinstance(content, list):
                parts = content
            elif hasattr(content, "parts"):
                parts = content.parts if hasattr(content, "parts") else [content]
            else:
                parts = [content]

            api_messages.append({"role": api_role, "parts": parts})

        return api_messages

    def get_last_n_messages(self, n: int) -> list[Message]:
        """Get the last N messages from history.

        Args:
            n: Number of messages to retrieve

        Returns:
            List of last N messages
        """
        return self.messages[-n:] if n > 0 else []

    def _maybe_truncate(self) -> None:
        """Truncate history if it exceeds limits."""
        if len(self.messages) > self.max_messages:
            self.truncate()

    def truncate(self) -> None:
        """Apply truncation strategy to reduce message count.

        Strategies:
        - oldest_first: Remove oldest messages (keeping system context)
        - importance_based: Remove low-importance messages first
        """
        if self.truncation_strategy == "oldest_first":
            self._truncate_oldest_first()
        elif self.truncation_strategy == "importance_based":
            self._truncate_importance_based()
        else:
            self._truncate_oldest_first()

    def _truncate_oldest_first(self) -> None:
        """Remove oldest messages to fit within limit.

        Keeps the most recent messages, removing from the beginning.
        Tries to keep user/model message pairs together.
        """
        target_count = int(self.max_messages * 0.8)
        if len(self.messages) <= target_count:
            return

        to_remove = len(self.messages) - target_count

        if to_remove % 2 == 1 and to_remove < len(self.messages):
            to_remove += 1

        self.messages = self.messages[to_remove:]
        logger.debug(f"Truncated history: removed {to_remove} messages, {len(self.messages)} remaining")

    def _truncate_importance_based(self) -> None:
        """Remove messages based on importance scoring.

        Importance factors:
        - Recent messages are more important
        - Tool call/result pairs should stay together
        - User commands are important landmarks
        """
        # For now, fall back to oldest_first
        # TODO: Implement proper importance scoring
        self._truncate_oldest_first()

    def summarize(self, summarizer_func: Optional[callable] = None) -> None:
        """Summarize old messages into a condensed context message.

        This replaces old messages with a single summary message to preserve
        context while reducing token count.

        Args:
            summarizer_func: Optional function that takes messages and returns summary.
                           If None, uses a simple concatenation approach.
        """
        if len(self.messages) <= 5:
            return

        messages_to_summarize = self.messages[:-5]
        recent_messages = self.messages[-5:]

        if summarizer_func:
            summary = summarizer_func(messages_to_summarize)
        else:
            summary_parts = []
            for msg in messages_to_summarize:
                role = msg["role"].value if isinstance(msg["role"], MessageRole) else str(msg["role"])
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    summary_parts.append(f"[{role}]: {content[:100]}...")

            summary = "Previous conversation summary:\n" + "\n".join(summary_parts[-10:])

        summary_message: Message = {
            "role": MessageRole.USER,
            "content": f"[CONTEXT SUMMARY]\n{summary}",
        }

        self.messages = [summary_message] + recent_messages
        logger.debug(f"Summarized history: condensed to {len(self.messages)} messages")

    def clear(self) -> None:
        """Clear all conversation history."""
        self.messages = []

    def __len__(self) -> int:
        """Return number of messages in history."""
        return len(self.messages)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ConversationHistory({len(self.messages)} messages, max={self.max_messages})"
