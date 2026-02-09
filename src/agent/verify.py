import io
import json
import logging
from typing import Any, Dict, List, Optional

from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

from agent.brain import get_gemini_client

logger = logging.getLogger(__name__)


def verify_task_completion(
    user_command: str,
    expected_result: str,
    screen_elements: List[Dict],
    original_path: str,
    debug_path: str,
    reference_sheet,
    task_history: List[Dict],
) -> Optional[Dict[str, Any]]:
    """
    Verify that a task was actually completed by analyzing the current screen state.

    Args:
        user_command: Original user command
        expected_result: What the AI expected to happen
        screen_elements: Current UI elements detected
        original_path: Path to screenshot
        debug_path: Path to annotated screenshot
        reference_sheet: Reference sheet image
        task_history: List of actions taken

    Returns:
        Dict with verification result:
        {
            "is_complete": bool,
            "confidence": float (0-1),
            "reasoning": str,
            "next_action": Optional[str]
        }
    """
    try:
        clean_image = Image.open(original_path)
        annotated_image = Image.open(debug_path)
    except Exception:
        logger.exception("Error loading images for verification")
        return None

    class VerificationResult(BaseModel):
        is_complete: bool = Field(
            description="True if the task is verifiably complete based on visual evidence"
        )
        confidence: float = Field(description="Confidence score spanning 0.0 to 1.0")
        reasoning: str = Field(
            description="Explanation of what visual evidence supports this conclusion"
        )
        next_action: Optional[str] = Field(
            description="Suggestion for the next step if task is not complete, or null/None if complete"
        )

    elements_str = "\n".join(
        [f"ID {el['id']}: {el['type']} '{el['label']}'" for el in screen_elements[:100]]
    )

    history_str = "\n".join(
        [
            f"Step {i + 1}: {action['action_type']} - {action['reasoning']}"
            for i, action in enumerate(task_history)
        ]
    )

    prompt_text = f"""
You are an AI OS Agent tasked with VERIFYING task completion.

ORIGINAL USER COMMAND: "{user_command}"
EXPECTED RESULT: "{expected_result}"

ACTIONS TAKEN:
{history_str}

CURRENT SCREEN ELEMENTS:
{elements_str}

ATTACHMENTS:
1. [Current Screen]: Shows the current state after all actions
2. [Annotated Screen]: Shows UI elements with IDs (use for reference)

YOUR TASK:
Carefully analyze the current screen state and determine if the user's original command
has been ACTUALLY COMPLETED.

VERIFICATION CRITERIA:
- Does the screen show evidence that the task was completed?
- Are the expected UI elements visible? (e.g., if "Open Notepad", is Notepad visible?)
- Does the current state match what was expected?

RESPONSE FORMAT:
Return a JSON object satisfying the VerificationResult schema.
"""

    def _image_to_part(img: Image.Image) -> types.Part:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        return types.Part.from_bytes(
            data=img_byte_arr.getvalue(),
            mime_type="image/png",
        )

    parts = [
        {"text": prompt_text},
        _image_to_part(clean_image),
        _image_to_part(annotated_image),
    ]
    if reference_sheet:
        parts.append(_image_to_part(reference_sheet))

    try:
        response = get_gemini_client().generate_structured(
            contents=[{"role": "user", "parts": parts}],
            response_schema=VerificationResult.model_json_schema(),
        )

        result_obj = VerificationResult.model_validate_json(response.text)
        return result_obj.model_dump()

    except Exception:
        logger.exception("Error during verification")
        return None
