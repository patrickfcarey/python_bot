# Developer Guide - Diablo II Offline AI Bot

This guide explains architecture, modules, lifecycle, testing, and extension points for developers and AI agents.

## 1. Project Overview

Pipeline:
1. Vision captures and interprets automap frames.
2. `GameState` represents structured world state.
3. `StateManager` tracks high-level lifecycle.
4. `CommandModule` can override policy actions.
5. Policy generates `Action`.
6. Controller executes actions via keyboard/mouse.
7. Main loop runs at controlled FPS.

## 2. Module Responsibilities

### `bot/config.py`
- Global constants and runtime knobs.
- Includes control keys, template/screenshot paths, vision thresholds, and debug toggle.

### `bot/game_state.py`
- Defines `GameState` dataclass.
- Stores player position, teammate positions, relative vectors, loading flag, level number, optional `last_action`.

### `bot/controller.py`
- Defines `Action` container (`click_target`, `cast_spell`, `stop`).
- Executes low-level keyboard/mouse behavior.

### `bot/vision.py`
- Captures automap region and extracts state.
- Loading detection uses brightness threshold.
- Teammate detection uses template matching and OCR gate.

### `bot/policy/rule_policy.py`
- Baseline rule policy.
- Uses first relative vector and `TURN_SENSITIVITY` to pick click target.

### `bot/policy/ml_policy.py`
- Stub for model-backed policy replacement.

### `bot/state_manager.py`
- Tracks `loading`, `new_level`, `playing`.
- Uses `LEVEL_STABILIZE_TIME` from config.

### `bot/command_module.py`
- FIFO queue of override `Action` objects.

### `bot/utils/timing.py`
- FPS limiter helper.

### `bot/main.py`
- Entry point for orchestrating capture -> state -> decision -> control.

## 3. Data Flow

- Vision -> `GameState`
- `GameState` -> StateManager
- `GameState` -> CommandModule / Policy
- Action -> Controller
- Repeat at target FPS

## 4. Lifecycle

1. Capture frame
2. Build `GameState`
3. Update lifecycle state
4. Pull override command if available
5. Otherwise run policy
6. Execute action
7. Wait for FPS budget

## 5. Testing

Run from repo root:

```bash
python -m pytest bot/tests -q
```

Tests currently cover:
- Rule policy output shape
- State manager transition behavior
- Controller movement key behavior (mocked)

## 6. Extension Points

- Replace `RulePolicy` with ML policy that maps `GameState -> Action`
- Add richer command types in `CommandModule`
- Extend vision pipeline with stronger detector models
- Add dataset logging around `(state, action)` pairs

## 7. Recommended Workflow

1. Create/activate venv
2. Install dependencies
3. Run tests
4. Implement change
5. Re-run tests
6. Update docs if behavior or structure changed

## 8. Notes for AI Developers

- Entry point: `python -m bot.main`
- Keep Vision, Policy, and Controller decoupled
- Keep offline-only usage constraints explicit
- Favor deterministic tests over live-input tests