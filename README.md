# Diablo II Offline AI Bot

**Version:** 1.0  
**Author:** Your Name  
**Purpose:** AI bot for offline Diablo II gameplay to follow teammates and interact with the game environment using computer vision, relative automap tracking, and rule-based decision making.  

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Launching the Bot](#launching-the-bot)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Lifecycle](#lifecycle)
- [Contributing](#contributing)
- [License](#license)

---

## Project Overview

This project implements an offline AI bot for **Diablo II**, designed for private offline servers. It uses:

- **Computer Vision (OpenCV, OCR)** for detecting teammates on the automap.
- **Relative tracking** for player and teammate positions.
- **Rule-based policy** to follow teammates and execute actions.
- Optional hooks for future **imitation learning or reinforcement learning**.

> ⚠️ Works **only on offline servers** you control. Does not interface with live servers.

---

## Features

- Detect teammates on the automap (green X + name OCR)
- Track player position on the automap
- Compute relative vectors to teammates
- Rule-based AI to follow teammates
- Modular command module for temporary overrides
- Configurable movement sensitivity and thresholds
- Logging and debug overlay support
- Fully testable (unit + integration)

---

## System Requirements

- Python 3.11+
- Libraries: `opencv-python`, `pytesseract`, `pyautogui`, `mss`, `numpy`, `pytest`
- Windows recommended (for pyautogui)
- Offline Diablo II with automap enabled

---

## Installation

```bash
git clone <repo_url>
cd diablo2-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

Ensure tesseract is installed and in your system PATH for OCR.

Configuration

All configurable values are in config.py:

Config	Purpose	Default
AUTOMAP_REGION	Screen region for the automap capture	top-left 800x600
LOADING_BRIGHTNESS_THRESHOLD	Determines loading screen detection	30
LEVEL_STABILIZE_TIME	Time to wait after level load	2.0 s
TURN_SENSITIVITY	Scaling factor for relative movement	0.2
MOVE_KEY, STOP_KEY	Keys for movement	"w", "s"
SPELL_KEYS	Map for spell keys	{"primary": "1"}
DEBUG	Prints debug info	True
SCREENSHOT_PATH	Path to store test screenshots	"screenshots/"
TEMPLATE_PATH	Path to teammate X template	"templates/green_x.png"

Adjust AUTOMAP_REGION if your game is running at a different resolution.

Launching the Bot
python main.py
Debug logs will print positions, teammates, and actions.
Stop the bot with Ctrl+C.
The bot will automatically pause on loading screens.


Testing
Unit Tests
pytest tests/
Includes tests for:
RulePolicy decisions
Relative vector calculations
GameState construction
Mocked Controller actions
Integration Tests
Place sample screenshots in tests/screenshots/
Run vision tests to verify teammate detection and OCR calibration.
Project Structure
diablo2-bot/
│
├── config.py
├── game_state.py
├── controller.py
├── vision.py
├── policy/
│   └── rule_policy.py
├── state_manager.py
├── command_module.py
├── utils/
│   └── timing.py
├── main.py
├── templates/
│   └── green_x.png
├── tests/
│   ├── test_rule_policy.py
│   └── screenshots/
├── README.md
└── DEVELOPER_GUIDE.md
Lifecycle
Vision: capture screen → detect player, teammates, and loading screen.
GameState Construction: store player position, teammate positions, relative vectors, level number, loading flag.
StateManager: track high-level bot state (loading, new_level, playing).
CommandModule: check for queued manual override commands.
Policy: decide next action using GameState (default: follow nearest teammate).
Controller: execute action via simulated keyboard/mouse.
Loop: repeat at 30 FPS (configurable in FPSLimiter).