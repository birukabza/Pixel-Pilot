import time
from typing import Optional
import pyautogui
import pyperclip

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

try:
    import keyboard as _third_party_keyboard
except Exception:
    _third_party_keyboard = None


def add_hotkey(hotkey, callback, suppress: bool = False, timeout: Optional[float] = None):
    """Register a global hotkey using the third-party `keyboard` package if present."""
    if _third_party_keyboard:
        return _third_party_keyboard.add_hotkey(
            hotkey, callback, suppress=suppress, timeout=timeout
        )
    raise RuntimeError(
        "third-party 'keyboard' package is not available; install it for hotkey support"
    )


def send(keys, do_press: bool = True):
    """Send key presses via third-party `keyboard` if available."""
    if _third_party_keyboard:
        return _third_party_keyboard.send(keys, do_press=do_press)
    raise RuntimeError("third-party 'keyboard' package is not available; install it to use `send`")


class KeyboardController:
    """
    Handles all keyboard-related operations for the AI agent.
    """

    KEY_MAPPING = {
        "enter": "enter",
        "return": "enter",
        "tab": "tab",
        "space": "space",
        "backspace": "backspace",
        "delete": "delete",
        "esc": "esc",
        "escape": "esc",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "home": "home",
        "end": "end",
        "pageup": "pageup",
        "pagedown": "pagedown",
        "insert": "insert",
        "capslock": "capslock",
        "numlock": "numlock",
        "scrolllock": "scrolllock",
        "win": "win",
        "windows": "win",
        "cmd": "command",
        "command": "command",
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        **{f"f{i}": f"f{i}" for i in range(1, 13)},
    }

    def __init__(self):
        """Initialize the keyboard controller."""
        self.last_action_time = time.time()

    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """
        Type the given text.

        Args:
            text: The text to type
            interval: Time delay between keystrokes (default 0.05 seconds)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Typing: '{text}'")
            pyautogui.write(text, interval=interval)
            self.last_action_time = time.time()
            return True
        except Exception as e:
            print(f"Error typing text: {e}")
            return False

    def press_key(self, key: str, presses: int = 1) -> bool:
        """
        Press a single key or special key.

        Args:
            key: The key to press (e.g., 'enter', 'tab', 'a')
            presses: Number of times to press the key

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key_lower = key.lower()
            actual_key = self.KEY_MAPPING.get(key_lower, key_lower)

            print(f"Pressing key: '{actual_key}' ({presses}x)")
            pyautogui.press(actual_key, presses=presses)
            self.last_action_time = time.time()
            return True
        except Exception as e:
            print(f"Error pressing key '{key}': {e}")
            return False

    def key_combo(self, *keys: str) -> bool:
        """
        Press a combination of keys (e.g., Ctrl+C, Alt+Tab).

        Args:
            *keys: Variable number of keys to press together

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            actual_keys = [self.KEY_MAPPING.get(key.lower(), key.lower()) for key in keys]

            print(f"Key combination: {'+'.join(actual_keys)}")
            pyautogui.hotkey(*actual_keys)
            self.last_action_time = time.time()
            return True
        except Exception as e:
            print(f"Error with key combo {'+'.join(keys)}: {e}")
            return False

    def hold_key(self, key: str, duration: float = 0.5) -> bool:
        """
        Hold down a key for a specified duration.

        Args:
            key: The key to hold
            duration: How long to hold the key in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key_lower = key.lower()
            actual_key = self.KEY_MAPPING.get(key_lower, key_lower)

            print(f"Holding key: '{actual_key}' for {duration}s")
            pyautogui.keyDown(actual_key)
            time.sleep(duration)
            pyautogui.keyUp(actual_key)
            self.last_action_time = time.time()
            return True
        except Exception as e:
            print(f"Error holding key '{key}': {e}")
            return False

    def copy_to_clipboard(self, text: str) -> bool:
        """
        Copy text to clipboard.

        Args:
            text: Text to copy

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Copying to clipboard: '{text[:50]}...'")
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False

    def paste_from_clipboard(self) -> bool:
        """
        Paste text from clipboard using Ctrl+V.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            clipboard_content = pyperclip.paste()
            print(f"Pasting from clipboard: '{clipboard_content[:50]}...'")
            self.key_combo("ctrl", "v")
            self.last_action_time = time.time()
            return True
        except Exception as e:
            print(f"Error pasting from clipboard: {e}")
            return False

    def get_clipboard_text(self) -> Optional[str]:
        """
        Get current clipboard text.

        Returns:
            str: Clipboard text or None if error
        """
        try:
            return pyperclip.paste()
        except Exception as e:
            print(f"Error getting clipboard text: {e}")
            return None

    def select_all(self) -> bool:
        """
        Select all text (Ctrl+A).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "a")

    def copy(self) -> bool:
        """
        Copy selected text (Ctrl+C).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "c")

    def paste(self) -> bool:
        """
        Paste clipboard content (Ctrl+V).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.paste_from_clipboard()

    def cut(self) -> bool:
        """
        Cut selected text (Ctrl+X).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "x")

    def undo(self) -> bool:
        """
        Undo last action (Ctrl+Z).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "z")

    def redo(self) -> bool:
        """
        Redo last undone action (Ctrl+Y).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "y")

    def save(self) -> bool:
        """
        Save file (Ctrl+S).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "s")

    def open_start_menu(self) -> bool:
        """
        Open Windows Start menu (Win key).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.press_key("win")

    def alt_tab(self) -> bool:
        """
        Switch windows (Alt+Tab).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("alt", "tab")

    def close_window(self) -> bool:
        """
        Close current window (Alt+F4).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("alt", "f4")

    def new_tab(self) -> bool:
        """
        Open new browser tab (Ctrl+T).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "t")

    def close_tab(self) -> bool:
        """
        Close current browser tab (Ctrl+W).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "w")

    def refresh_page(self) -> bool:
        """
        Refresh page (F5 or Ctrl+R).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.press_key("f5")

    def search(self) -> bool:
        """
        Open search (Ctrl+F).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.key_combo("ctrl", "f")


keyboard_controller = KeyboardController()


def type_text(text: str, interval: float = 0.05) -> bool:
    """Type text using the global keyboard controller."""
    return keyboard_controller.type_text(text, interval)


def press_key(key: str, presses: int = 1) -> bool:
    """Press a key using the global keyboard controller."""
    return keyboard_controller.press_key(key, presses)


def key_combo(*keys: str) -> bool:
    """Press a key combination using the global keyboard controller."""
    return keyboard_controller.key_combo(*keys)


if __name__ == "__main__":
    print("Testing Keyboard Controller...")
    print("\n1. Testing key press (Enter)...")
    time.sleep(2)
    keyboard_controller.press_key("enter")

    print("\n2. Testing key combo (Ctrl+C)...")
    time.sleep(1)
    keyboard_controller.key_combo("ctrl", "c")

    print("\n3. Testing clipboard...")
    keyboard_controller.copy_to_clipboard("Hello from AI Agent!")
    time.sleep(1)
    print(f"Clipboard content: {keyboard_controller.get_clipboard_text()}")

    print("\n Keyboard Controller tests complete!")
