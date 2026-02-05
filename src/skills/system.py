import keyboard
import ctypes
import os


class SystemSkill:
    """
    Controls system functions like Volume, Power, and Window Management using native calls.
    """

    def __init__(self):
        self.enabled = True
        print("System Skill: Enabled (Volume, Power, Windows)")

    def set_volume(self, action):
        """
        Control volume. action: 'up', 'down', 'mute'
        """
        try:
            if action == "up":
                for _ in range(3):
                    keyboard.send("volume up")
                return "Increased volume"
            elif action == "down":
                for _ in range(3):
                    keyboard.send("volume down")
                return "Decreased volume"
            elif action == "mute":
                keyboard.send("volume mute")
                return "Toggled mute"
            else:
                return f"Unknown volume action: {action}"
        except Exception as e:
            return f"Error setting volume: {e}"

    def lock_screen(self):
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Locked workstation"
        except Exception as e:
            return f"Error locking screen: {e}"

    def minimize_all(self):
        try:
            keyboard.send("win+d")
            return "Toggled Desktop (Minimize/Restore All)"
        except Exception as e:
            return f"Error minimizing: {e}"

    def open_settings(self, page=None):
        """
        Open Windows Settings.
        """
        try:
            uri = "ms-settings:"
            if page:
                uri += page
            os.system(f"start {uri}")
            return f"Opened Settings ({page or 'Home'})"
        except Exception as e:
            return f"Error opening settings: {e}"
