# Developer Guide - Diablo II Offline AI Bot

This guide explains the **architecture, modules, functions, lifecycle, testing, and extension points** for developers or AI agents working on this project.

---

## 1. Project Overview

The bot is designed for **offline Diablo II servers only**. It follows a **modular pipeline**:

1. Vision: capture screen, detect player & teammates, calculate relative vectors.
2. GameState: structured representation of the environment.
3. StateManager: tracks high-level states (`loading`, `new_level`, `playing`).
4. CommandModule: allows temporary override actions (manual commands, spell casting, etc.).
5. Policy: decision logic (currently rule-based, ML-ready).
6. Controller: executes actions via simulated mouse/keyboard.
7. Main Loop: orchestrates the pipeline at ~30 FPS.

---

## 2. Module Responsibilities

### `config.py`
- Contains all constants and configurable parameters.
- Key variables:
  - `AUTOMAP_REGION` - screen coordinates for automap
  - `LOADING_BRIGHTNESS_THRESHOLD`
  - `LEVEL_STABILIZE_TIME`
  - `TURN_SENSITIVITY`
  - Movement and spell keys (`MOVE_KEY`, `STOP_KEY`, `SPELL_KEYS`)
  - `DEBUG`, `SCREENSHOT_PATH`, `TEMPLATE_PATH`

### `game_state.py`
- Defines `GameState` class.
- Stores:
  - `player_position` `(x, y)`
  - `teammate_positions` `[(x, y), ...]`
  - `relative_vectors` `[(dx, dy), ...]` (player → teammate)
  - `level_number`
  - `loading` flag
  - Optional `last_action` for ML logging

### `controller.py`
- `Action` class: holds `click_target`, `cast_spell`, `stop`
- `Controller` class:
  - `click(x, y)` → simulates mouse click
  - `cast_spell(slot)` → presses spell key
  - `move_forward(on=True)` → holds/releases move key
  - `stop_all()` → releases all movement keys

### `vision.py`
- Captures the screen and converts frames to `GameState`.
- Key functions:
  - `grab_frame()` → screenshot of automap region
  - `is_loading(frame)` → detects loading screen via brightness
  - `get_player_position(frame)` → returns player coordinates
  - `find_teammates(frame)` → detects green X + OCR nameplate
  - `extract_game_state(frame, level_number)` → returns full GameState, including relative vectors

### `policy/rule_policy.py`
- Default decision logic:
  - `decide(GameState) -> Action`
  - Follows first teammate using `relative_vectors`
  - Scales movement with `TURN_SENSITIVITY`
- Fully replaceable with ML or RL policies.

### `state_manager.py`
- Tracks high-level bot state:
  - `"loading"` → game is loading
  - `"new_level"` → level has changed
  - `"playing"` → normal gameplay
- Handles **level stabilization timing**.

### `command_module.py`
- Queue of manual override Actions.
- Methods:
  - `add_command(Action)` → queue new command
  - `get_next()` → dequeue next action
- Overrides Policy if queue is non-empty.

### `utils/timing.py`
- `FPSLimiter(fps)` → `wait()` method to maintain consistent loop speed

### `main.py`
- Main execution loop:
  1. Grab frame → Vision
  2. Construct GameState
  3. Update StateManager
  4. Check CommandModule for queued commands
  5. If none → Policy decides next Action
  6. Controller executes Action
  7. Wait for FPS limiter → repeat

---

## 3. Data Flow

- Vision converts raw frames into structured GameState.
- GameState is used by:
  - Policy for decision making.
  - StateManager to track high-level state.
  - CommandModule for manual override actions.
- Controller executes Actions produced by Policy or CommandModule.
- The loop repeats continuously at controlled FPS.

---

## 4. Lifecycle of the Bot

1. **Frame Capture**: Vision grabs automap frame.
2. **Teammate Detection**: Vision detects green X + OCR for names.
3. **Relative Vector Calculation**: compute player → teammate vectors.
4. **GameState Construction**: stores positions, vectors, level, loading flag.
5. **StateManager Update**: determines `"loading"`, `"new_level"`, or `"playing"`.
6. **CommandModule Check**: execute queued overrides if any.
7. **Policy Decision**: default is rule-based following teammate.
8. **Controller Execution**: clicks, moves, and casts spells.
9. **FPS Limiting**: maintain stable loop (~30 FPS).

---

## 5. Testing

### Unit Tests
- Located in `tests/`.
- Mock `GameState` and `Controller` for safe testing.
- Run all unit tests with:
pytest tests/

- Verify:
  - RulePolicy outputs
  - Relative vector computation
  - CommandModule queue behavior
  - StateManager state transitions

### Integration Tests
- Use screenshots for Vision testing.
- Verify:
  - Teammate detection accuracy
  - OCR name recognition
  - Relative vectors correctness
  - Policy → Action correctness
- Adjust `AUTOMAP_REGION` for different resolutions if needed.

---

## 6. Extension Points

- **Policy Replacement**
  - Replace `RulePolicy` with ML model: `GameState → Action`.
  - Input: `relative_vectors`, `player_position`, `teammate_positions`.
  - Output: `Action.click_target`, `Action.cast_spell`, `Action.stop`.

- **Imitation Learning / Reinforcement Learning**
  - Use `last_action` from GameState to store `(state, action)` pairs.
  - Can be used for training future ML policies.

- **CommandModule Enhancements**
  - Manual spell casting, skill allocation, reporting inventory.
  - Testing risky behavior without altering default Policy.

- **Multi-Teammate Coordination**
  - Currently follows first teammate only.
  - Future versions can implement prioritization, distance-based decisions, or multi-agent coordination.

---

## 7. Recommended Development Workflow

1. Pull latest repo.
2. Activate Python virtual environment.
3. Run unit tests:
pytest tests/


4. Run integration tests on sample screenshots.
5. Modify/add Policy, Vision, or Controller modules.
6. Debug with `DEBUG=True`.
7. Lint with `flake8` and format with `black`.
8. Commit changes with clear messages.

---

## 8. Notes for AI Developers

- **Entry point:** `main.py`
- **Key input data:** `GameState.relative_vectors`, `player_position`, `teammate_positions`
- **Key output:** `Action` executed via Controller
- **CommandModule:** safe override mechanism
- **Vision & Controller decoupled:** always maintain separation
- **Offline only:** ensures ethical compliance
- **Debug/logging:** critical for training and testing new policies

> This guide ensures any AI or human agent can safely extend, test, or replace modules while preserving separation of concerns.