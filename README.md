# Diablo II Offline AI Bot

**Version:** 1.0
**Author:** Patrick Carey
**Purpose:** AI bot for offline Diablo II gameplay to follow teammates and interact with the game environment using computer vision, relative automap tracking, and rule-based decision making.

## Project Overview

This project implements an offline AI bot for Diablo II, designed for private offline servers.

Core design:
- Computer Vision (OpenCV + OCR) for teammate detection on automap
- Relative tracking for player and teammate positions
- Rule-based policy for baseline follow behavior
- Clean extension points for future imitation learning or reinforcement learning

This project is intended for offline/private environments only.

## Features

- Detect teammates on the automap (template match + OCR gate)
- Track player position on the automap
- Compute relative vectors to teammates
- Rule-based policy to follow teammates
- Command queue for temporary manual overrides
- Configurable movement sensitivity and thresholds
- Logging support for debug and future data collection

## System Requirements

- Python 3.11+
- Windows recommended (for `pyautogui` reliability)
- Diablo II offline/private setup with automap enabled
- Tesseract installed and available on your system `PATH`

## Installation

```bash
git clone <repo_url>
cd python_bot
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

All configurable values are in [bot/config.py](bot/config.py).

Key settings:
- `AUTOMAP_REGION`: screen region for automap capture
- `LOADING_BRIGHTNESS_THRESHOLD`: loading screen brightness threshold
- `LEVEL_STABILIZE_TIME`: wait time after level change
- `TURN_SENSITIVITY`: movement scaling factor
- `MOVE_KEY`, `STOP_KEY`, `SPELL_KEYS`: control mapping
- `TEMPLATE_PATH`: teammate marker template path
- `SCREENSHOT_PATH`: integration-test screenshot folder
- `DEBUG`: debug logging toggle

## Launching the Bot

From repository root:

```bash
python -m bot.main
```

Stop with `Ctrl+C`.

## Testing

Run tests from repository root:

```bash
python -m pytest bot/tests -q
```

Current suite includes:
- Rule policy decision checks
- State manager transition checks
- Mocked controller input checks

For vision integration tests, place screenshots in `bot/tests/screenshots/`.

## Project Structure

See [folder_structure.md](folder_structure.md).

## Lifecycle

1. Vision captures automap frame.
2. Vision extracts `GameState` (player, teammates, relative vectors, loading flag).
3. `StateManager` updates lifecycle state (`loading`, `new_level`, `playing`).
4. `CommandModule` may override next action.
5. Policy decides action from `GameState`.
6. Controller executes action.
7. Loop repeats at fixed FPS.

## Contributing

1. Run tests before committing.
2. Keep Vision, Policy, and Controller decoupled.
3. Keep docs aligned with actual code and file paths.

## License

MIT (see [LICENSE](LICENSE)).