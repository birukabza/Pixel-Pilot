import os


class TimerSkill:
    """
    Interacts with Windows Alarms & Clock app via URI schemes.
    """

    def __init__(self):
        self.enabled = True
        print("Timer Skill: Enabled (Windows Clock)")

    def open_timer(self):
        try:
            os.system("start ms-clock:timer")
            return "Opened Windows Clock (Timer tab). Please set the time manually."
        except Exception as e:
            return f"Error opening timer: {e}"

    def open_alarm(self):
        try:
            os.system("start ms-clock:alarm")
            return "Opened Windows Clock (Alarm tab)."
        except Exception as e:
            return f"Error opening alarm: {e}"

    def open_stopwatch(self):
        try:
            os.system("start ms-clock:stopwatch")
            return "Opened Windows Clock (Stopwatch tab)."
        except Exception as e:
            return f"Error opening stopwatch: {e}"
