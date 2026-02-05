# PixelPilot

![PixelPilot Logo](src/logos/pixelpilot-logo-creative.svg)

**Pilot Your Pixels.**

PixelPilot is a Windows desktop automation agent powered by **Gemini (Google GenAI SDK)** + computer vision. It translates natural language commands into real-time mouse + keyboard actions, can use “skills” for common tasks (media/browser/system), and includes an optional Secure Desktop helper for UAC prompts.

## Features

### Advanced AI & Vision
*   **Gemini planning model**: Uses the `GEMINI_MODEL` you configure (default: `gemini-3-flash-preview`).
*   **Two vision modes** (switch in the UI dropdown):
    *   **ROBO (default)**: Gemini Robotics-ER (`gemini-robotics-er-1.5-preview`) for semantic UI understanding.
    *   **OCR**: Local **EasyOCR + OpenCV** (“OCR+Edge”) element detection.
*   **Lazy Vision fallback**: If robotics is unavailable, PixelPilot falls back to OCR.
*   **Magnification**: Supports a magnify action to zoom into dense areas.
*   **Reference sheets**: Builds a grid of cropped UI elements (when enabled) to help the model reason over small UI parts.

### Secure Desktop (UAC) Integration
*   **UAC Orchestrator (optional)**: The installer can create a scheduled task that runs an orchestrator as **SYSTEM** on startup.
*   **Trigger-based**: When PixelPilot detects Secure Desktop (black screenshot / access denied), it writes a trigger file:
    *   `%SystemRoot%\Temp\uac_trigger.txt`
*   **Snapshot + decision**:
    *   The injected UAC agent saves `%SystemRoot%\Temp\uac_snapshot.bmp`
    *   PixelPilot writes `%SystemRoot%\Temp\uac_response.txt` with `ALLOW` / `DENY`

### Safety Modes
*   **GUIDANCE**: Suggests the next step (does not execute it).
*   **SAFE**: Prompts before **every** action.
*   **AUTO**: Runs autonomously, but prompts on actions that look dangerous (best-effort heuristic).

### Performance & Tools
*   **Turbo Mode**: Can execute a short sequence of sub-actions in one step.
*   **Smart App Indexer**: Uses Start Menu shortcuts + processes cache to find apps fast.
*   **Loop Detection**: Detects repeated screen states and attempts to recover.
*   **Media / Browser / System skills**: Uses OS APIs where possible instead of UI driving.
*   **Voice input**: Mic button uses `SpeechRecognition` (Google Web Speech) for speech-to-text.

## Quick Start

### 1. Installation

Run the installer to set up the Python environment and (optionally) the UAC orchestrator + launcher tasks.

```bash
python install.py
```
*   **Virtual Environment**: Creates `venv` and installs dependencies from `requirements.txt`.
*   **UAC Helper EXEs**: Compiles `src/uac/orchestrator.py` and `src/uac/agent.py` with PyInstaller.
*   **Scheduled Tasks**:
    *   `PixelPilotUACOrchestrator` (runs as **SYSTEM** on startup)
    *   `PixelPilotApp` (launcher task; the Desktop shortcut runs this task)
*   **Desktop Shortcut**: Creates `Pixel Pilot.lnk` that runs `schtasks /RUN /TN "PixelPilotApp"`.

Optional (deps only, no scheduled tasks/shortcut):

```bash
python install.py --no-tasks
```

### 2. Configuration

Create a `.env` file in the repository root (next to `install.py`):

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-flash-preview
DEFAULT_MODE=auto
VISION_MODE=robo
```

Tip: you can start from `env.example`.

Notes:
*   `DEFAULT_MODE` should be `guide`, `safe`, or `auto`.
*   `VISION_MODE` should be `robo` (Gemini Robotics-ER) or `ocr` (local OCR+CV).

### 3. Run

**Method 1: Desktop Shortcut (Recommended)**
Double-click the **PixelPilot** shortcut. This launches the agent with the necessary permissions to communicate with the UAC Orchestrator.

**Method 2: Command Line**
```bash
.\venv\Scripts\python.exe .\src\main.py
```

Notes:
*   PixelPilot is GUI-first (PySide6). You can change **Mode** and **Vision** from the dropdowns.
*   On Windows, PixelPilot will attempt to relaunch itself with Administrator privileges. If you decline, it will continue with limited automation.
*   Logs are written to `logs/pixelpilot.log` (and installer launcher logs to `logs/app_launch.log`).

### Hotkeys (system-wide)
*   `Ctrl+Shift+Z` — Toggle click-through (overlay interactive ↔ click-through)
*   `Ctrl+Shift+X` — Stop current request
*   `Ctrl+Shift+Q` — Quit PixelPilot

## Architecture

PixelPilot uses a multi-process architecture to bridge the gap between userland and the Secure Desktop.

1.  **Main App (`src/main.py`)**:
    *   Runs in the user's session.
    *   Provides the PySide6 UI and routes agent output into the GUI.
    *   Captures screenshots, plans actions with Gemini, and executes input (Mouse/Keyboard).
    *   Detects Secure Desktop/UAC symptoms (black screen / access denied during capture).
    *   Triggers the Orchestrator via `%SystemRoot%\Temp\uac_trigger.txt`.

2.  **Orchestrator Service (`src/uac/orchestrator.py`)**:
    *   Runs as **SYSTEM** (via Task Scheduler on boot).
    *   Watches for the trigger signal.
    *   When triggered, it uses Windows APIs (including `CreateProcessAsUserW`) to launch a specialized **UAC Agent** into the `WinLogon` Secure Desktop session.

3.  **Vision Pipeline**:
    *   **Capture**: Uses `mss` first (when possible), then falls back to `pyautogui`.
    *   **Analysis**:
        *   **ROBO**: Gemini Robotics-ER for element detection (with optional bounding boxes).
        *   **OCR**: EasyOCR + OpenCV contour/icon candidates.
    *   **Planning**: Sends the screenshot + an annotated overlay (ID tags) to Gemini.

## Usage Examples

**Natural Language Commands:**
*   "Open Calculator and calculate 25 * 34"
*   "Find Spotify and play the next song"
*   "Open device manager as admin" (Triggers UAC Orchestrator)
*   "Search Google for 'Python tutorials' and open the first link"

PixelPilot runs as a standard desktop GUI app; close the window to exit.

## Troubleshooting

*   If the app opens and closes immediately, verify `.env` has `GEMINI_API_KEY`.
*   Check logs in `logs/pixelpilot.log`.
*   If UAC handling doesn’t work:
    *   Re-run `python install.py` as Administrator to recreate the scheduled task.
    *   Verify the `PixelPilotUACOrchestrator` scheduled task is running.

## License

MIT

---

**Made with Gemini + computer vision.**
