import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agent.brain import get_gemini_client
logger = logging.getLogger(__name__)
from config import Config, OperationMode


class ClarificationQuestion(BaseModel):
    question: str = Field(description="The specific question to ask the user")
    options: Optional[List[str]] = Field(description="Optional multiple choice options")


class RefinedAction(BaseModel):
    action_type: str = Field(description="The corrected action type")
    params: Dict[str, Any] = Field(description="Updated action parameters")
    reasoning: str = Field(description="Updated reasoning based on user feedback")
    confidence: float = Field(
        default=1.0, description="Confidence score (set to 1.0 after user confirmation)"
    )
    clarification_needed: bool = Field(
        default=False, description="Set to false after clarification"
    )
    task_complete: bool = Field(description="Whether the task is now complete")
    expected_result: str = Field(description="What should happen after this corrected action")


class ClarificationManager:
    """
    Manages user clarification when AI is uncertain about actions.
    Integrates with the agent to ask questions and incorporate user feedback.
    """

    def __init__(self, chat_window=None, mode: OperationMode = OperationMode.SAFE):
        """
        Initialize the clarification manager.

        Args:
            chat_window: Optional ChatWindow instance
            mode: Operation mode
        """
        self.chat_window = chat_window
        self.mode = mode
        self.clarification_history: List[Dict] = []

    def should_ask_clarification(self, action: Dict[str, Any]) -> bool:
        """
        Determine if clarification should be requested.

        Args:
            action: The planned action with confidence score

        Returns:
            True if clarification is needed
        """

        if not Config.ENABLE_CLARIFICATION:
            return False

        if self.mode == OperationMode.GUIDE:
            return True

        if action.get("clarification_needed", False):
            return True

        confidence = action.get("confidence", 1.0)
        if confidence < Config.CLARIFICATION_MIN_CONFIDENCE:
            return True

        return False

    def ask_question(self, action: Dict[str, Any], user_command: str) -> Optional[str]:
        """
        Ask the user a clarification question.

        Args:
            action: The action that needs clarification
            user_command: Original user command

        Returns:
            User's answer as string, or None if cancelled
        """

        question = action.get("clarification_question")

        if not question:
            question = self.generate_question(action, user_command)

        if not self.chat_window:
            return None

        return self.chat_window.ask_input("Clarification Needed", question)

    def present_options(
        self, options: List[str], question: str = "Please choose an option:"
    ) -> Optional[int]:
        """
        Present multiple choice options to the user.

        Args:
            options: List of option strings
            question: The question to ask

        Returns:
            Selected option index (0-based) or None if cancelled
        """
        if not self.chat_window:
            return None

        formatted = f"{question}\n\n"
        for i, opt in enumerate(options):
            formatted += f"{i + 1}. {opt}\n"

        answer = self.chat_window.ask_input("Choose an Option", formatted)
        if answer:
            try:
                choice = int(answer) - 1
                if 0 <= choice < len(options):
                    return choice
            except ValueError:
                pass
        return None

    def generate_question(self, action: Dict[str, Any], user_command: str) -> str:
        """
        Use AI to generate a clarification question.

        Args:
            action: The uncertain action
            user_command: Original user command

        Returns:
            Generated question string
        """
        try:
            confidence = action.get("confidence", 0.0)
            action_type = action.get("action_type", "unknown")
            reasoning = action.get("reasoning", "")

            prompt = f"""
You are helping an AI agent clarify an uncertain action.

USER COMMAND: "{user_command}"

AI's PLANNED ACTION:
- Type: {action_type}
- Parameters: {action.get("params", {})}
- Reasoning: {reasoning}
- Confidence: {confidence:.0%}

The AI is uncertain about this action. Generate a clear, specific question to ask the user
that will help clarify what action to take.

The question should:
1. Be concise and easy to understand
2. Offer specific choices when possible (A/B/C format)
3. Help resolve the uncertainty

Return JSON:
{{
    "question": "The specific question to ask",
    "options": ["Option A", "Option B", "Option C"]  // Optional: provide choices
}}
"""

            response = get_gemini_client().generate_structured(
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                response_schema=ClarificationQuestion.model_json_schema(),
            )

            result = ClarificationQuestion.model_validate_json(response.text)
            question = result.question
            options = result.options or []

            if options:
                formatted = f"{question}\n"
                for i, opt in enumerate(options, 1):
                    formatted += f"  ({chr(64 + i)}) {opt}\n"
                return formatted
            else:
                return question

        except Exception:
            logger.exception("Error generating clarification question")

            return f"I'm {confidence:.0%} confident about {action_type}. Can you provide more details about what you want to do?"

    def integrate_answer(
        self, action: Dict[str, Any], answer: str, user_command: str
    ) -> Optional[Dict[str, Any]]:
        """
        Integrate user's answer into the action plan.

        Args:
            action: Original uncertain action
            answer: User's response
            user_command: Original command

        Returns:
            Updated action dictionary or None if failed
        """
        try:
            self.clarification_history.append(
                {
                    "original_action": action,
                    "user_answer": answer,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            prompt = f"""
You are helping interpret user feedback to refine an AI action.

ORIGINAL USER COMMAND: "{user_command}"

ORIGINAL PLANNED ACTION:
{json.dumps(action, indent=2)}

USER'S CLARIFICATION/ANSWER:
"{answer}"

Based on the user's answer, provide the corrected/refined action.
Maintain the same JSON structure but update the parameters and reasoning as needed.
Set confidence to 1.0 since we now have user confirmation.

Return the updated action in the same JSON format:
{{
    "action_type": "<type>",
    "params": {{}},
    "reasoning": "<updated reasoning>",
    "confidence": 1.0,
    "clarification_needed": false,
    "task_complete": <bool>,
    "expected_result": "<what should happen>"
}}
"""

            response = get_gemini_client().generate_structured(
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                response_schema=RefinedAction.model_json_schema(),
            )

            return RefinedAction.model_validate_json(response.text).model_dump()

        except Exception:
            logger.exception("Error integrating clarification answer")

            action["clarification_needed"] = False
            return action

    def handle_loop_clarification(
        self, loop_info: Dict, user_command: str, suggestions: List[str]
    ) -> Optional[str]:
        """
        Special handler for when a loop is detected.

        Args:
            loop_info: Information about the detected loop
            user_command: Original user command
            suggestions: AI-generated alternative suggestions

        Returns:
            User's choice or instruction, or None if cancelled
        """
        loop_info.get("pattern", "unknown")
        count = loop_info.get("count", 0)

        message = f""" LOOP DETECTED

I've been stuck repeating the same action {count} times without progress.

Original goal: "{user_command}"

The AI suggests trying these alternatives:
"""

        options = suggestions + ["Let me describe a different approach", "Cancel this task"]

        if not self.chat_window:
            return None

        formatted = message
        for i, opt in enumerate(options, 1):
            formatted += f"\n{i}. {opt}"

        choice = self.chat_window.ask_input("Loop Detected - Need Help", formatted)
        if choice:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    if idx == len(options) - 1:
                        return None
                    return options[idx]
            except ValueError:
                return choice

        return None

    def clear_history(self):
        """Clear clarification history."""
        self.clarification_history.clear()

    def __repr__(self):
        return f"ClarificationManager(mode={self.mode}, history={len(self.clarification_history)})"
