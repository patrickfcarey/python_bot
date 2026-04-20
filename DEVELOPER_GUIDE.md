# Developer Guide - Diablo II Offline Bot

## Architecture

Runtime flow:
1. startup checks and logging setup
2. game window detection (title first, OCR fallback)
3. optional auto-centering
4. automap capture region derivation
5. frame capture -> state extraction -> policy/combat -> controller execution
6. optional performance monitoring and report export

Core modules:
- [bot/main.py](bot/main.py): CLI and orchestration
- [bot/config.py](bot/config.py): runtime configuration dataclass
- [bot/window_manager.py](bot/window_manager.py): window location and centering
- [bot/vision.py](bot/vision.py): capture and OCR-backed teammate detection + enemy scan stub
- [bot/enemy_tracker.py](bot/enemy_tracker.py): enemy track association stub
- [bot/combat.py](bot/combat.py): combat decision stubs
- [bot/performance.py](bot/performance.py): stage timing, FPS analysis, JSON report output
- [bot/policy/rule_policy.py](bot/policy/rule_policy.py): baseline follow behavior
- [bot/controller.py](bot/controller.py): input execution abstraction
- [bot/ocr_dataset.py](bot/ocr_dataset.py): OCR crop collector

## Commands

- `python -m bot.main center-window --debug`
- `python -m bot.main collect-ocr --samples 500 --interval 0.35 --debug`
- `python -m bot.main run --dry-run --debug --max-frames 300`
- `python -m bot.main run --dry-run --debug --enable-combat-stub --max-frames 300`
- `python -m bot.main run --debug`
- `python -m bot.main perf-test --target-fps 50 --fps 50 --warmup-frames 120 --frames 600 --synthetic --debug`

## Performance Framework

- `perf-test` captures per-frame stage timings:
  - `capture`
  - `vision`
  - `state`
  - `decision`
  - `control`
  - `sleep`
- it computes p50/p95/p99 frame-time, average achieved FPS, and target pass/fail
- it writes JSON reports under `logs/perf/` (or `--output-json` override)
- target FPS pass condition requires both average and p95 frame-time to satisfy target frame budget

## Production Notes

- `run_startup_checks` verifies tesseract availability and required directories.
- controller supports `dry_run` to prevent live input during verification.
- state transitions are controlled by `StateManager` and `BotLifecycle` enum.
- window centering is done before starting capture loop to stabilize automap region.
- combat stubs are opt-in behind `--enable-combat-stub`.

## Enemy/Combat Stubs

- `Vision.scan_enemies` is a placeholder heuristic and should be replaced with robust detection.
- `EnemyTracker` currently uses nearest-neighbor matching per frame.
- `CombatRoutine` currently chooses nearest tracked target and emits simple spell/move actions.
- Keep this path in dry-run until detection quality is validated.

## OCR Training Pipeline

Use [OCR_WORKFLOW.md](OCR_WORKFLOW.md).

Collection output:
- `data/ocr/raw/*.png`
- `data/ocr/raw/manifest.jsonl`

## Testing

```powershell
python -m pytest bot/tests -q
```

Current tests cover:
- policy behavior
- controller action execution
- lifecycle transitions
- command queue FIFO behavior
- region math for automap cropping
- enemy tracker ID continuity and timeout behavior
- combat stub decision behavior
- performance monitor summary and JSON reporting