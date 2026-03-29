# AI Developer Entry - Diablo II Offline Bot

## Purpose

This document is intended for **the next AI or human agent** who will work on this project.  
It provides:

- Architectural overview  
- Module responsibilities  
- Data flow  
- Design reasoning  
- Extension points for AI learning or advanced features  
- Safe practices for testing and integration  

> ⚠️ This bot is designed for **offline Diablo II servers only**. Do not attempt to run it on live servers.

---

## Project Overview

The bot follows a **modular pipeline**:

1. **Vision Module**: Captures the automap, detects player and teammates, calculates relative vectors.  
2. **GameState**: Structured representation of the current environment.  
3. **StateManager**: Tracks high-level states like `loading`, `new_level`, and `playing`.  
4. **CommandModule**: Allows temporary override actions (manual commands, spell casting, etc.).  
5. **Policy**: Decision logic, currently rule-based, can be replaced with ML models.  
6. **Controller**: Executes actions using simulated mouse and keyboard events.  
7. **Main Loop**: Orchestrates the pipeline at ~30 FPS.

---

## Module Responsibilities

| Module | Purpose | Key Functions | Notes |
|--------|--------|---------------|-------|
| `vision.py` | Convert game frames → structured info | `grab_frame()`, `is_loading()`, `get_player_position()`, `find_teammates()`, `extract_game_state()` | Calculates **relative vectors**. All ML inputs should come from `extract_game_state()` |
| `game_state.py` | Structured environment representation | `GameState` | Stores player/teammates positions, relative vectors, level, loading, optional `last_action` for training |
| `controller.py` | Low-level inputs | `Controller.click()`, `cast_spell()`, `move_forward()`, `stop_all()` | Should **never access Vision** |
| `policy/rule_policy.py` | Decision making | `decide(GameState) -> Action` | Uses `GameState.relative_vectors`. Replaceable with ML model |
| `state_manager.py` | High-level bot state | `update_state(GameState) -> str` | Tracks level transitions and loading |
| `command_module.py` | Manual override actions | `add_command()`, `get_next()` | Overrides policy when queue is non-empty |
| `utils/timing.py` | Loop timing | `FPSLimiter.wait()` | Ensures consistent FPS |

---

## Data Flow

1. **Vision → GameState**: convert raw frames to structured data.  
2. **GameState → StateManager**: update current bot state.  
3. **GameState → CommandModule**: check for queued overrides.  
4. **GameState → Policy**: generate `Action`.  
5. **Action → Controller**: execute mouse/keyboard events.  
6. **Loop**: repeat at controlled FPS.

[Screen Capture] → [Vision] → [GameState] → [StateManager] → [Policy/Command] → [Action] → [Controller] → repeat



---

## Key Design Decisions

- **Separation of concerns**: Vision (input) vs Controller (output) vs Policy (decision).  
- **Relative vectors**: Calculated once in Vision, stored in GameState → used by Policy.  
- **Last action**: Optional storage in GameState for future ML training.  
- **CommandModule**: Supports temporary overrides, ensuring safe testing for human/AI operators.  
- **Offline only**: To comply with legal and ethical restrictions.

---

## Extension Points

1. **Policy replacement**:  
   - RulePolicy can be replaced with an ML model mapping `GameState → Action`.  
   - Input: `relative_vectors`, `player_position`, `teammate_positions`.  
   - Output: `Action.click_target`, `Action.cast_spell`, `Action.stop`.

2. **Imitation Learning / RL hooks**:  
   - Store `(state, action)` pairs using `last_action`.  
   - Future policy modules can consume this dataset.

3. **Additional commands**:  
   - Add to CommandModule queue for spell casting, skill point allocation, or reporting inventory.

4. **Multi-agent coordination**:  
   - Currently supports following a single teammate.  
   - Can be extended to track multiple teammates and select priorities.

---

## Testing Guide

### Unit Tests

- Located in `tests/`
- Can **mock GameState** and Controller
- Use `pytest` to run all tests
- Examples:
  - RulePolicy decisions
  - Relative vector calculations

### Integration Tests

- Use screenshots for Vision module
- Validate OCR detection, teammate positions, relative vectors, and Policy actions
- Adjust `AUTOMAP_REGION` for resolution differences

---

## Safety & Best Practices for AI Agents

- Do **not** run Controller on live servers
- Always use `DEBUG=True` when testing new modules
- Keep Vision and Controller **decoupled**
- Use CommandModule for testing risky actions
- Store screenshots for OCR calibration and training
- Log GameState + Actions for ML training

---

## Recommended Development Workflow

1. Pull latest code
2. Activate virtual environment
3. Run unit tests
4. Run integration tests on sample screenshots
5. Add new module or modify Policy
6. Log outputs with `DEBUG=True`
7. Commit changes, lint with `flake8` and format with `black`

---

## Summary for the Next AI Agent

- **Entry point:** `main.py`  
- **Input:** game frames → Vision → GameState  
- **Decision:** Policy or CommandModule → Action  
- **Output:** Controller executes Action  
- **Key internal data:** `GameState.relative_vectors` (ML-ready), `GameState.last_action` (logging)  
- **Safe override mechanism:** CommandModule queue  
- **Testing:** unit + integration using `pytest` and screenshots

> This file serves as your **primary onboarding document**. Every change to Policy, Vision, or Controller must maintain 
the separation of concerns and preserve offline-only operation.