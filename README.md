# Diablo II Offline Bot (Production First Pass)

This repository includes a production-oriented first pass focused on:
- deterministic startup checks
- game window discovery and auto-centering before runtime
- CV + OCR teammate detection with dataset capture tooling
- enemy scanning/tracking/combat stubs for future combat systems
- measurable performance benchmarking with stage timing and target FPS checks
- clean CLI workflows for run, calibration, OCR collection, and perf testing

This project is intended for offline/private environments only.

## What Works Today

- CLI commands:
  - `run`
  - `center-window`
  - `collect-ocr`
  - `perf-test`
  - `ocr-bench`
- Window discovery by title keywords with OCR anchor fallback
- Auto-center behavior before runtime loop
- Automap capture region derived from detected game window
- Teammate candidate detection via green-marker segmentation + optional template match
- OCR validation on nameplate crops
- OCR crop collection utility with manifest output
- OCR augmentation script to expand one screenshot into many training variants
- Stubbed enemy pipeline:
  - `Vision.scan_enemies(frame)`
  - `EnemyTracker.update(detections)`
  - `CombatRoutine.decide(game_state)`
- Performance framework:
  - frame-stage timings (`capture`, `vision`, `state`, `decision`, `control`, `sleep`)
  - p50/p95/p99 frame-time stats
  - target FPS pass/fail check
  - JSON report output under `logs/perf/`
- Async vision path:
  - heavy full-frame analysis runs in a background worker
  - main control loop stays responsive and drops overloaded vision jobs
  - stale results fall back to a safe no-target state
- Observer pipeline:
  - non-blocking per-frame event capture into bounded queues
  - drop policy support (`drop_oldest`/`drop_new`) to protect FPS
  - background JSONL writer + scenario coverage snapshots
  - optional shadow-policy agreement scoring for online policy telemetry
  - optional low-rate full-frame samples and high-threat snapshots
- Manual runtime pause/resume hotkey: `Ctrl+Space` (toggle)

## System Requirements

- Windows 10/11
- Python 3.11+
- Tesseract OCR 5.x installed and available on `PATH`
- Diablo II in windowed/borderless-windowed mode for stable window control

## Python Dependencies

Install from [requirements.txt](requirements.txt):
- `opencv-python`
- `numpy`
- `pytesseract`
- `mss`
- `pyautogui`
- `pygetwindow`
- `pywin32`
- `pillow`
- `pytest`

## Installation

From `C:\github\python_bot`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Runtime Commands

Run window alignment only:

```powershell
python -m bot.main center-window --debug
```

Collect OCR crops (training data):

```powershell
python -m bot.main collect-ocr --samples 500 --interval 0.35 --debug
```

Collect OCR latency metrics (screenshot capture + OCR processing):

```powershell
python -m bot.main ocr-bench --samples 300 --fps 20 --mode both --synthetic --debug
```

Run OCR latency benchmark against live capture path:

```powershell
python -m bot.main ocr-bench --samples 200 --fps 20 --mode both --debug
```

Run bot in dry-run mode:

```powershell
python -m bot.main run --dry-run --debug --fps 60 --max-frames 300
```

Run bot with enemy/combat stubs enabled:

```powershell
python -m bot.main run --dry-run --debug --enable-combat-stub --max-frames 300
```

Run bot live:

```powershell
python -m bot.main run --debug
```

## First Live Run Checklist

Before your first non-dry-run session, pass this checklist in order:

1. Environment readiness:
- Tesseract is detected at startup (no startup OCR error).
- Diablo II is in windowed or borderless-windowed mode.
- `python -m bot.main center-window --debug` succeeds at least once.

2. Dry-run stability:
- `python -m bot.main run --dry-run --debug --fps 60 --max-frames 300` completes without crashes.
- No repeated capture/window exceptions in `logs/bot.log`.

3. OCR sanity:
- `python -m bot.main ocr-bench --samples 200 --fps 20 --mode both --debug` finishes cleanly.
- OCR output quality is acceptable on real motion samples (not only synthetic).

4. Performance sanity:
- `python -m bot.main perf-test --target-fps 50 --fps 50 --warmup-frames 120 --frames 600 --synthetic --debug` passes target.
- Live-capture perf test is reviewed before enabling combat stubs.

5. Short live smoke test:
- Start with `python -m bot.main run --debug --max-frames 120`.
- Keep combat stubs off for first live smoke test.

Expected run artifacts (healthy observer/perf pipeline):
- `logs/bot.log`
- `logs/observer/observer_events_*.jsonl`
- `logs/observer/coverage_latest.json`
- `logs/observer/shadow_metrics_latest.json`
- `logs/observer/observer_stats_latest.json`
- `logs/observer/observer_images_index.jsonl` (when frame sampling is enabled)
- `logs/observer/frame_samples/*.jpg` (when frame sampling is enabled)
- `logs/perf/perf_report_*.json` (when `perf-test` is run)
- `logs/perf/ocr_bench_report_*.json` (when `ocr-bench` is run)

## Async Vision Tuning

- default uses bounded async scheduling (`vision_async_enabled=True`, `vision_async_workers=2`, `vision_async_max_pending_jobs=4`)
- stale-drop policy is latest-frame-first: when pending queue is full, oldest queued jobs are cancelled so newer frames can enter
- if all workers are busy and nothing can be cancelled, new submissions are dropped via backpressure to protect frame-time stability
- set `--vision-max-age-ms <value>` to control result freshness cutoff
- set `--vision-workers <n>` and `--vision-max-pending <n>` to tune worker concurrency and queue depth
- set `--sync-vision` to compare against synchronous processing

## Observer Data Pipeline

- Observer capture is enabled by default (`observer_enabled=True`) and runs in background threads so the main loop stays non-blocking.
- Event stream is written to JSONL files under `logs/observer/observer_events_*.jsonl`.
- Scenario coverage snapshot is continuously updated at `logs/observer/coverage_latest.json`.
- Optional frame samples are written under `logs/observer/frame_samples/` and indexed in `logs/observer/observer_images_index.jsonl`.
- Shadow-policy summary is continuously updated at `logs/observer/shadow_metrics_latest.json` and evaluated events include a `shadow` object in JSONL rows.

Core observer knobs in [bot/config.py](bot/config.py):
- `observer_event_queue_size`, `observer_event_batch_size`, `observer_flush_interval_ms`
- `observer_drop_policy` (`drop_oldest` recommended for freshness)
- `observer_capture_full_frames`, `observer_full_frame_sample_fps`
- `observer_high_threat_frame_capture`, `observer_high_threat_min_danger`, `observer_high_threat_cooldown_s`
- `observer_shadow_enabled`, `observer_shadow_include_loading`, `observer_shadow_min_confidence`

Runtime overrides (`run` / `perf-test`):
- `--observer-off`
- `--observer-event-queue <n>`
- `--observer-image-queue <n>`
- `--observer-batch-size <n>`
- `--observer-flush-ms <ms>`
- `--observer-sample-fps <fps>`
- `--observer-high-threat-min-danger <priority>`
- `--observer-shadow-off`
- `--observer-shadow-min-confidence <0..1>`
- `--observer-shadow-include-loading`

Coverage reporting:

```powershell
python scripts/coverage_report.py --input logs/observer --target-per-bucket 300 --top 20
```

## In-Game Chat Commands (OCR)

The bot can read in-game chat lines via OCR and execute control commands in real time.

Expected format in Diablo II chat:
- `<sender>: !<command> [arg]`
- Example: `Leader: !stop`

Supported commands:
- `!stop` / `!pause` / `!hold`: pause follow and issue immediate stop action.
- `!follow` / `!resume` / `!go`: resume follow behavior.
- `!follow off`: pause follow behavior.
- `!combat on|off|auto`: runtime combat-toggle override.
- `!pickup on|off|auto`: runtime loot-toggle override.
- `!potion on|off|auto`: runtime potion-toggle override.
- `!cast <slot>`: queue a spell cast using configured spell slot key mapping.
- `!tp` / `!town`: queue town portal cast.
- `!reset` / `!auto`: clear pause/toggle overrides.

Security and parsing controls:
- `--chat-command-senders "Leader,Support"` restricts accepted senders.
- `--chat-command-require-sender` rejects OCR lines without sender token.
- `--chat-command-prefix "!"` sets prefix token.
- `--chat-command-allow-no-prefix` allows command parsing without prefix (less strict).
- `--chat-commands-off` disables chat command OCR path.
- `--pause-hotkey-off` disables Ctrl+Space pause/resume toggle.
- `--pause-hotkey-debounce-ms <ms>` sets combo debounce (default 300ms).

Example run:
```powershell
python -m bot.main run --dry-run --debug --chat-command-senders "Leader" --chat-command-require-sender
```

## Character Profiles

Use `--profile` to switch behavior by character.

Available profiles:
- `legacy` (uses top-level runtime values)
- `balanced`
- `sorc_tele`
- `hammerdin`
- `frenzy_barb`
- `necromancer`

`follow_radius` behavior:
- profile-specific `follow_radius` defines acceptable distance from the followed ally
- inside this radius the bot holds position (no movement click)
- outside this radius the bot clicks toward a radius-adjusted point instead of directly on top of the ally

Necromancer stub behavior:
- includes nested necromancer config values (`follow_radius`, curse/primary/summon spell slots, recast frame intervals)
- combat stub spell selection uses a function-based necro spell chooser for future expansion

Examples:
```powershell
python -m bot.main run --dry-run --debug --profile sorc_tele --max-frames 300
python -m bot.main run --dry-run --debug --enable-combat-stub --profile hammerdin --max-frames 300
python -m bot.main run --dry-run --debug --enable-combat-stub --profile necromancer --max-frames 300
```

## Performance Testing Framework

Run a measurable benchmark targeting 50 FPS:

```powershell
python -m bot.main perf-test --target-fps 50 --fps 50 --warmup-frames 120 --frames 600 --synthetic --debug
```

Run benchmark against live capture path:

```powershell
python -m bot.main perf-test --target-fps 50 --fps 50 --warmup-frames 120 --frames 600 --debug
```

Perf report output:
- default: `logs/perf/perf_report_YYYYMMDD_HHMMSS.json`
- override: `--output-json <path>`
- includes `annotations` with vision scheduler metadata (`vision_mode`, `vision_max_age_ms`, `vision_async_workers`, `vision_async_max_pending_jobs`) and async counters (`vision_async_submitted`, `vision_async_completed`, `vision_async_dropped`, `vision_async_dropped_stale`, `vision_async_dropped_backpressure`, `vision_async_inflight_count`, `vision_async_drop_rate`)

OCR benchmark report output:
- default: `logs/perf/ocr_bench_report_YYYYMMDD_HHMMSS.json`
- override: `--output-json <path>`
- stage metrics include `capture`, `teammate_ocr`, and `ground_ocr` p50/p95/p99/max

## Timed Gameplay Routines

- Belt potion management, ground item OCR scans, pickit matching, and gold pickup checks now run on independent timers.
- Core timer knobs are in [bot/config.py](bot/config.py): `resource_scan_interval_s`, `belt_scan_interval_s`, `ground_item_scan_interval_s`, `buff_check_interval_s`, `merc_check_interval_s`, `inventory_check_interval_s`.
- Pickup rules are loaded from `data/pickit/default_pickit.json` (or `RuntimeConfig.pickit_db_path`).
- Potion actions use slots: `health_potion_action_slot`, `mana_potion_action_slot`, `rejuvenation_potion_action_slot` mapped through `spell_keys`.
- Safety defaults skip pickup behavior while enemies are actively tracked (`pickup_disable_when_enemies=True`).

## OCR Augmentation Script

Script path:
- [scripts/augment_ocr_dataset.py](scripts/augment_ocr_dataset.py)

Single screenshot -> many variants:

```powershell
python scripts/augment_ocr_dataset.py `
  --input data/ocr/raw/example.png `
  --output-dir data/ocr/augmented/example `
  --variants-per-image 120 `
  --seed 42
```

## Enemy/Combat Stub Notes

Current combat path is intentionally a scaffold:
- enemy scan uses a red-marker heuristic placeholder
- tracker uses simple nearest-neighbor association
- combat routine uses weighted target selection (`target_priority_score`, danger, consensus, pressure ratings) with distance as a soft penalty
- danger and threat metadata now flows through detections/tracks (`danger_*`, vectors, consensus, pressure ratings, mitigation hints) and is consumed by the combat selector
- combat tags now include broader categories (for example `ranged_attacker`, `life_drain`, `mana_drain`, elemental tags, summon/control tags) with `archer` retained as an alias for all ranged attackers

Safety:
- combat stubs are disabled by default (`enable_combat_stub=False`)
- explicitly pass `--enable-combat-stub` to activate

## OCR Training and Dataset Requirements

Use [DATA_REQUIREMENTS.md](DATA_REQUIREMENTS.md) for exact required files, paths, filename schemes, and examples.

Full workflow and count targets are in [OCR_WORKFLOW.md](OCR_WORKFLOW.md).

Enemy hover-name OCR and monster image-recognition dataset structure is in [MONSTER_DATA_STRUCTURE.md](MONSTER_DATA_STRUCTURE.md).

Threat-tier rationale and consensus sources for `critical`/`super_critical` are in [THREAT_CONSENSUS.md](THREAT_CONSENSUS.md).

Threat variable definitions are in [MONSTER_THREAT_VARIABLES.md](MONSTER_THREAT_VARIABLES.md).

Build grouped monster families and combat-risk profiles with:
`python scripts/build_monster_family_groups.py`

Generated monster outputs include:
- `data/web_seed_pack/processed/monsters/monster_family_groups.csv`
- `data/web_seed_pack/processed/monsters/monster_combat_profiles.csv`
- `data/web_seed_pack/processed/monsters/monster_family_summary.json`

Minimum raw targets:
- ally automap names: `1,400` screenshots (`40` names x `35` each)
- command message OCR: `2,600` chat-line screenshots (`1,600` command positives + `1,000` negatives)

Generated OCR data locations:
- raw crops: `data/ocr/raw/`
- labeled samples: `data/ocr/labeled/`
- augmented outputs: `data/ocr/augmented/` (create as needed)

## Window Detection/Centering Requirements

For reliable window management:
- run game in windowed or borderless windowed mode
- ensure game title or on-screen text includes at least one configured keyword
- update keywords in [bot/config.py](bot/config.py) if your client differs

Startup path:
1. locate window by title keyword match
2. fallback to OCR screen anchor if title match fails
3. activate and center window
4. derive automap region from centered window
5. start vision/control loop

## Tests

```powershell
python -m pytest bot/tests -q
```

## Key Files

- runtime config: [bot/config.py](bot/config.py)
- main CLI/runtime: [bot/main.py](bot/main.py)
- performance framework: [bot/performance.py](bot/performance.py)
- observer worker: [bot/observer.py](bot/observer.py)
- observer event schema: [bot/observer_schema.py](bot/observer_schema.py)
- shadow-policy scorer: [bot/shadow_policy.py](bot/shadow_policy.py)
- scenario coverage tracker: [bot/coverage.py](bot/coverage.py)
- vision pipeline: [bot/vision.py](bot/vision.py)
- timed gameplay scanner/planner: [bot/gameplay.py](bot/gameplay.py)
- pickit rule loader/matcher: [bot/pickit.py](bot/pickit.py)
- enemy tracker stub: [bot/enemy_tracker.py](bot/enemy_tracker.py)
- combat stub: [bot/combat.py](bot/combat.py)
- OCR collector: [bot/ocr_dataset.py](bot/ocr_dataset.py)
- OCR augmentation script: [scripts/augment_ocr_dataset.py](scripts/augment_ocr_dataset.py)
- monster dataset guide: [MONSTER_DATA_STRUCTURE.md](MONSTER_DATA_STRUCTURE.md)
- monster dataset validator: [scripts/validate_monster_dataset.py](scripts/validate_monster_dataset.py)
- observer coverage report script: [scripts/coverage_report.py](scripts/coverage_report.py)
- startup checks/logging: [bot/runtime_checks.py](bot/runtime_checks.py)

## License

MIT ([LICENSE](LICENSE)).








