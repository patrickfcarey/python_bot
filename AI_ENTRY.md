# AI Entry Notes

Entry point:
- `python -m bot.main <command>`

Main commands:
- `run`
- `center-window`
- `collect-ocr`
- `perf-test`

Combat stub toggle:
- `python -m bot.main run --enable-combat-stub --dry-run --debug`

Performance benchmark example (50 FPS target):
- `python -m bot.main perf-test --target-fps 50 --fps 50 --warmup-frames 120 --frames 600 --synthetic --debug`

Startup sequence:
1. runtime checks (`bot/runtime_checks.py`)
2. locate/center window (`bot/window_manager.py`)
3. create capture region
4. vision loop (`bot/vision.py`)
5. optional enemy scan/track/combat stubs (`bot/enemy_tracker.py`, `bot/combat.py`)
6. optional perf instrumentation (`bot/performance.py`)
7. policy decision (`bot/policy/rule_policy.py`)
8. execute action (`bot/controller.py`)

Failure triage order (stop at the first failing stage):
1. Window detect/center:
   - run `python -m bot.main center-window --debug`
   - fix title matching/focus/position issues first
2. Frame capture path:
   - run `python -m bot.main run --dry-run --debug --max-frames 120`
   - verify no repeated capture-region or screenshot exceptions
3. OCR pipeline:
   - run `python -m bot.main ocr-bench --samples 200 --fps 20 --mode both --debug`
   - verify teammate-name/chat recognition quality on real motion scenes
4. Action timing/performance:
   - run synthetic then live `perf-test` and compare frame-time p95/p99
   - tune fps, vision age, worker/pending limits before live control changes
5. Combat stubs and advanced behavior:
   - only enable `--enable-combat-stub` after stages 1-4 are stable
   - triage target selection and danger-tag behavior last

OCR training/data:
- see `OCR_WORKFLOW.md`
- required file list/schemes in `DATA_REQUIREMENTS.md`
- enemy monster dataset structure in `MONSTER_DATA_STRUCTURE.md`
- raw capture output goes to `data/ocr/raw`
- curated labels should be stored in `data/ocr/labeled`
- validate monster coverage with `python scripts/validate_monster_dataset.py`

Key operational guardrails:
- use `--dry-run` first for all new behavior
- keep window mode deterministic (windowed/borderless windowed)
- combat stub path is experimental and disabled by default
- perf reports go to `logs/perf/` and should be reviewed before live tuning
- keep docs and config aligned whenever workflow changes
- use `Ctrl+Space` during runtime to pause/resume the bot (disable with `--pause-hotkey-off`)

Profile selection:
- pass `--profile <name>` on `run`, `center-window`, `collect-ocr`, or `perf-test`
- available: `legacy`, `balanced`, `sorc_tele`, `hammerdin`, `frenzy_barb`, `necromancer`
- `follow_radius` is used directly by follow policy to stop movement when inside acceptable ally distance
- `necromancer` profile includes function-driven spell-cast stub behavior in combat routine

Async vision scheduling:
- default runtime uses a background worker for full-frame vision processing
- main loop keeps running at target FPS and consumes freshest available result
- stale or missing worker results fall back to a safe no-target state
- enemy detections/tracks now carry optional danger metadata (`danger_priority`, `danger_label`, `danger_tags`, `combat_relevant`) so targeting/avoidance code can consume it later without changing current behavior
- use `--vision-max-age-ms <value>` to tune freshness threshold
- use `--sync-vision` on `run`/`perf-test` to disable background worker for comparison

Timed gameplay routines:
- periodic scanner (`bot/gameplay.py`) runs independent timers for resource bars, belt slots, ground-item OCR, buff/merc/inventory checks
- pickit matching uses `data/pickit/default_pickit.json` via `bot/pickit.py`
- planner prioritizes potion usage, then pickit/gold pickup, then standard combat/follow decisions
- tune cadence and thresholds in `RuntimeConfig` (`resource_scan_interval_s`, `belt_scan_interval_s`, `ground_item_scan_interval_s`, `health_potion_trigger_ratio`, `mana_potion_trigger_ratio`, `pickup_click_cooldown_s`)

In-game chat OCR commands:
- accepted line pattern: `<sender>: !<command> [arg]`
- examples: `Leader: !stop`, `Leader: !follow`, `Leader: !combat off`, `Leader: !pickup auto`, `Leader: !cast curse`, `Leader: !tp`
- runtime overrides are persisted in `CommandModule` (pause/combat/pickup/potion) until reset
- tune/lock down with `--chat-command-senders`, `--chat-command-require-sender`, `--chat-command-prefix`, `--chat-command-allow-no-prefix`
- disable entirely with `--chat-commands-off`
Observer data pipeline:
- enabled by default and runs asynchronously in `bot/observer.py`
- writes structured per-frame events to `logs/observer/observer_events_*.jsonl`
- updates scenario coverage summary at `logs/observer/coverage_latest.json`
- updates shadow-policy agreement metrics at `logs/observer/shadow_metrics_latest.json`
- optional frame samples are written to `logs/observer/frame_samples/`
- disable per run with `--observer-off`
- tune queue/flush with `--observer-event-queue`, `--observer-batch-size`, `--observer-flush-ms`
- tune shadow scoring with `--observer-shadow-off`, `--observer-shadow-min-confidence`, `--observer-shadow-include-loading`
- generate a gap report with `python scripts/coverage_report.py --input logs/observer --target-per-bucket 300 --top 20`

