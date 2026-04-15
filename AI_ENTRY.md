# AI Developer Entry - Diablo II Offline Bot

This document onboards the next AI or human contributor quickly.

## Purpose

- Explain architecture and module boundaries
- Show current data flow
- Highlight safe extension points
- Keep development focused on offline/private usage

## Current Architecture

1. Vision (`bot/vision.py`) converts automap frames into structured data.
2. `GameState` (`bot/game_state.py`) stores normalized state.
3. `StateManager` (`bot/state_manager.py`) tracks lifecycle state.
4. `CommandModule` (`bot/command_module.py`) supports override actions.
5. Policy (`bot/policy/*`) maps state to action.
6. Controller (`bot/controller.py`) executes keyboard/mouse commands.
7. Main loop (`bot/main.py`) orchestrates all modules.

## Module Boundaries

- Vision should not call Controller.
- Controller should not parse vision state.
- Policy should depend on `GameState`, not raw frames.
- `CommandModule` should remain a simple override layer.

## Data Flow

[Capture] -> [Vision] -> [GameState] -> [StateManager + Policy/Command] -> [Action] -> [Controller] -> repeat

## Extension Points

- Replace `RulePolicy` with an ML-backed policy adapter.
- Add logging/export of `(state, action)` for imitation learning.
- Improve teammate detection quality in `vision.py`.
- Expand command queue semantics for scripted behaviors.

## Testing Guidance

Run tests from repo root:

```bash
python -m pytest bot/tests -q
```

For vision integration testing:
- Store sample frames in `bot/tests/screenshots/`
- Keep tests deterministic and replayable

## Operational Safety

- Treat this as offline/private automation only.
- Never test live keyboard/mouse behaviors against unintended targets.
- Prefer mocked-controller tests by default.

## Quick Start For Next Agent

1. Read `README.md` and this file.
2. Run tests.
3. Verify config in `bot/config.py`.
4. Start bot with `python -m bot.main` once dependencies are installed.
5. Keep docs synchronized with code changes.