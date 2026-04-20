"""CLI entrypoint for runtime, calibration, OCR capture, and performance tests."""

import argparse
from dataclasses import replace
from pathlib import Path
import time
from typing import Callable, Dict, Optional, Tuple

import cv2
import numpy as np

from bot.combat import CombatDecision, CombatRoutine
from bot.chat_commands import ChatCommandProcessor
from bot.command_module import CommandModule
from bot.config import RuntimeConfig, default_config, profile_names
from bot.hotkeys import PauseHotkeyMonitor
from bot.controller import Action, Controller
from bot.enemy_tracker import EnemyTracker
from bot.game_state import GameState
from bot.gameplay import GameplayActionPlanner, GameplayScanner
from bot.ocr_benchmark import JSONOCRBenchmarkReporter, OCRBenchmarkSample, OCRLatencyMonitor
from bot.ocr_dataset import OCRDatasetCollector
from bot.observer import ObserverWorker
from bot.observer_schema import ObservationEvent, classify_party_size_band, classify_threat_band, sanitize_scenario_tags
from bot.performance import JSONPerfReporter, PerformanceMonitor, timing_from_stages
from bot.pickit import PickitDatabase
from bot.policy.rule_policy import RulePolicy
from bot.runtime_checks import configure_logging, run_startup_checks
from bot.state_manager import StateManager
from bot.utils.timing import FPSLimiter
from bot.vision import Vision
from bot.vision_async import AsyncVisionRunner
from bot.window_manager import GameWindowManager


FrameProvider = Callable[[], np.ndarray]


def _add_profile_argument(cmd: argparse.ArgumentParser):
    """Internal helper to add profile argument.

    Parameters:
        cmd: Parameter for cmd used in this routine.

    Local Variables:
        profiles: Local variable for profiles used in this routine.

    Returns:
        None.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    profiles = ", ".join(profile_names())
    cmd.add_argument(
        "--profile",
        type=str,
        default="",
        help=f"Character behavior profile override. Available: {profiles}",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build parser.

    Parameters:
        None.

    Local Variables:
        center_cmd: Local variable for center cmd used in this routine.
        collect_cmd: Local variable for collect cmd used in this routine.
        ocr_bench_cmd: Local variable for ocr bench cmd used in this routine.
        parser: Local variable for parser used in this routine.
        perf_cmd: Local variable for perf cmd used in this routine.
        run_cmd: Local variable for run cmd used in this routine.
        sub: Local variable for sub used in this routine.

    Returns:
        A value matching the annotated return type `argparse.ArgumentParser`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    parser = argparse.ArgumentParser(description="Diablo II offline bot runtime")

    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Start the bot loop")
    run_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    run_cmd.add_argument("--dry-run", action="store_true", help="Disable live keyboard/mouse actions")
    run_cmd.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = infinite)")
    run_cmd.add_argument("--fps", type=int, default=0, help="Optional override for loop FPS")
    run_cmd.add_argument(
        "--enable-combat-stub",
        action="store_true",
        help="Enable stub enemy scan/track/combat path for future combat development",
    )
    run_cmd.add_argument(
        "--sync-vision",
        action="store_true",
        help="Run full vision synchronously in main loop (background worker disabled)",
    )
    run_cmd.add_argument(
        "--vision-max-age-ms",
        type=float,
        default=0.0,
        help="Override max age for async vision results before fallback (0 uses config default)",
    )
    run_cmd.add_argument(
        "--vision-workers",
        type=int,
        default=0,
        help="Override async vision worker count (0 uses config default)",
    )
    run_cmd.add_argument(
        "--vision-max-pending",
        type=int,
        default=0,
        help="Override max async pending vision jobs (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-off",
        action="store_true",
        help="Disable observer worker/event capture for this run",
    )
    run_cmd.add_argument(
        "--observer-event-queue",
        type=int,
        default=0,
        help="Override observer event queue size (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-image-queue",
        type=int,
        default=0,
        help="Override observer image queue size (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-batch-size",
        type=int,
        default=0,
        help="Override observer event batch size (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-flush-ms",
        type=int,
        default=0,
        help="Override observer flush interval in milliseconds (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-sample-fps",
        type=float,
        default=-1.0,
        help="Override observer periodic full-frame sample FPS (-1 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-high-threat-min-danger",
        type=int,
        default=0,
        help="Override minimum danger priority for high-threat frame snapshots (0 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-shadow-off",
        action="store_true",
        help="Disable observer shadow-policy agreement scoring",
    )
    run_cmd.add_argument(
        "--observer-shadow-min-confidence",
        type=float,
        default=-1.0,
        help="Override minimum confidence for shadow-policy scoring (0..1, -1 uses config default)",
    )
    run_cmd.add_argument(
        "--observer-shadow-include-loading",
        action="store_true",
        help="Include non-playing/loading lifecycle events in shadow-policy scoring",
    )
    run_cmd.add_argument(
        "--chat-commands-off",
        action="store_true",
        help="Disable OCR in-game chat command controls",
    )
    run_cmd.add_argument(
        "--chat-command-prefix",
        type=str,
        default="",
        help="Override in-game chat command prefix token (empty uses config default)",
    )
    run_cmd.add_argument(
        "--chat-command-senders",
        type=str,
        default="",
        help="Comma-separated allowlist of sender names for chat commands",
    )
    run_cmd.add_argument(
        "--chat-command-require-sender",
        action="store_true",
        help="Require sender name in OCR chat lines before accepting commands",
    )
    run_cmd.add_argument(
        "--chat-command-allow-no-prefix",
        action="store_true",
        help="Allow command parsing without prefix token (less strict)",
    )
    run_cmd.add_argument(
        "--pause-hotkey-off",
        action="store_true",
        help="Disable Ctrl+Space runtime pause/resume hotkey",
    )
    run_cmd.add_argument(
        "--pause-hotkey-debounce-ms",
        type=float,
        default=-1.0,
        help="Override Ctrl+Space debounce in milliseconds (-1 uses config default)",
    )
    _add_profile_argument(run_cmd)

    center_cmd = sub.add_parser("center-window", help="Locate and center the game window")
    center_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    _add_profile_argument(center_cmd)

    collect_cmd = sub.add_parser("collect-ocr", help="Capture OCR training crops from automap")
    collect_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    collect_cmd.add_argument("--samples", type=int, default=300, help="Number of OCR crops to save")
    collect_cmd.add_argument("--interval", type=float, default=0.35, help="Seconds between capture rounds")
    collect_cmd.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Optional output override (default: config OCR raw dir)",
    )
    _add_profile_argument(collect_cmd)

    perf_cmd = sub.add_parser("perf-test", help="Run measurable frame-loop performance benchmark")
    perf_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    perf_cmd.add_argument("--enable-combat-stub", action="store_true", help="Include combat stubs in perf path")
    perf_cmd.add_argument("--target-fps", type=float, default=50.0, help="Target measured FPS threshold")
    perf_cmd.add_argument("--fps", type=int, default=50, help="Loop limiter FPS for benchmark")
    perf_cmd.add_argument("--frames", type=int, default=600, help="Number of sampled frames")
    perf_cmd.add_argument("--warmup-frames", type=int, default=120, help="Warmup frames excluded from summary")
    perf_cmd.add_argument("--synthetic", action="store_true", help="Use synthetic frame provider (no screen capture)")
    perf_cmd.add_argument(
        "--synthetic-image",
        type=str,
        default="",
        help="Optional path to image used as synthetic frame source",
    )
    perf_cmd.add_argument(
        "--live-input",
        action="store_true",
        help="Allow live keyboard/mouse actions during perf test (default is dry-run)",
    )
    perf_cmd.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional explicit path for perf JSON report",
    )
    perf_cmd.add_argument(
        "--sync-vision",
        action="store_true",
        help="Run full vision synchronously in main loop (background worker disabled)",
    )
    perf_cmd.add_argument(
        "--vision-max-age-ms",
        type=float,
        default=0.0,
        help="Override max age for async vision results before fallback (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--vision-workers",
        type=int,
        default=0,
        help="Override async vision worker count (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--vision-max-pending",
        type=int,
        default=0,
        help="Override max async pending vision jobs (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-off",
        action="store_true",
        help="Disable observer worker/event capture for this benchmark",
    )
    perf_cmd.add_argument(
        "--observer-event-queue",
        type=int,
        default=0,
        help="Override observer event queue size (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-image-queue",
        type=int,
        default=0,
        help="Override observer image queue size (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-batch-size",
        type=int,
        default=0,
        help="Override observer event batch size (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-flush-ms",
        type=int,
        default=0,
        help="Override observer flush interval in milliseconds (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-sample-fps",
        type=float,
        default=-1.0,
        help="Override observer periodic full-frame sample FPS (-1 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-high-threat-min-danger",
        type=int,
        default=0,
        help="Override minimum danger priority for high-threat frame snapshots (0 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-shadow-off",
        action="store_true",
        help="Disable observer shadow-policy agreement scoring",
    )
    perf_cmd.add_argument(
        "--observer-shadow-min-confidence",
        type=float,
        default=-1.0,
        help="Override minimum confidence for shadow-policy scoring (0..1, -1 uses config default)",
    )
    perf_cmd.add_argument(
        "--observer-shadow-include-loading",
        action="store_true",
        help="Include non-playing/loading lifecycle events in shadow-policy scoring",
    )
    perf_cmd.add_argument(
        "--chat-commands-off",
        action="store_true",
        help="Disable OCR in-game chat command controls",
    )
    perf_cmd.add_argument(
        "--chat-command-prefix",
        type=str,
        default="",
        help="Override in-game chat command prefix token (empty uses config default)",
    )
    perf_cmd.add_argument(
        "--chat-command-senders",
        type=str,
        default="",
        help="Comma-separated allowlist of sender names for chat commands",
    )
    perf_cmd.add_argument(
        "--chat-command-require-sender",
        action="store_true",
        help="Require sender name in OCR chat lines before accepting commands",
    )
    perf_cmd.add_argument(
        "--chat-command-allow-no-prefix",
        action="store_true",
        help="Allow command parsing without prefix token (less strict)",
    )
    perf_cmd.add_argument(
        "--pause-hotkey-off",
        action="store_true",
        help="Disable Ctrl+Space runtime pause/resume hotkey",
    )
    perf_cmd.add_argument(
        "--pause-hotkey-debounce-ms",
        type=float,
        default=-1.0,
        help="Override Ctrl+Space debounce in milliseconds (-1 uses config default)",
    )
    _add_profile_argument(perf_cmd)

    ocr_bench_cmd = sub.add_parser("ocr-bench", help="Benchmark screenshot capture + OCR processing latency")
    ocr_bench_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")
    ocr_bench_cmd.add_argument("--samples", type=int, default=300, help="Number of benchmark samples")
    ocr_bench_cmd.add_argument("--fps", type=int, default=20, help="Loop limiter FPS for benchmark sampling")
    ocr_bench_cmd.add_argument(
        "--mode",
        choices=("teammate", "ground", "both"),
        default="both",
        help="Which OCR path to benchmark",
    )
    ocr_bench_cmd.add_argument(
        "--ground-max-labels",
        type=int,
        default=12,
        help="Max labels passed to ground-item OCR scan",
    )
    ocr_bench_cmd.add_argument("--synthetic", action="store_true", help="Use synthetic frame provider (no screen capture)")
    ocr_bench_cmd.add_argument(
        "--synthetic-image",
        type=str,
        default="",
        help="Optional path to image used as synthetic frame source",
    )
    ocr_bench_cmd.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional explicit path for OCR benchmark JSON report",
    )
    _add_profile_argument(ocr_bench_cmd)

    return parser


def make_config(args: argparse.Namespace) -> RuntimeConfig:
    """Make config.

    Parameters:
        args: Parameter for args used in this routine.

    Local Variables:
        available: Local variable for available used in this routine.
        cfg: Local variable containing configuration values that guide behavior.
        requested: Local variable for requested used in this routine.

    Returns:
        A value matching the annotated return type `RuntimeConfig`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    cfg = default_config()

    if hasattr(args, "debug") and args.debug:
        cfg = replace(cfg, debug=True)

    if hasattr(args, "dry_run") and args.dry_run:
        cfg = replace(cfg, dry_run=True)

    if hasattr(args, "max_frames") and args.max_frames:
        cfg = replace(cfg, max_frames=args.max_frames)

    if hasattr(args, "fps") and args.fps:
        cfg = replace(cfg, fps=args.fps)

    if hasattr(args, "enable_combat_stub") and args.enable_combat_stub:
        cfg = replace(cfg, enable_combat_stub=True)

    if hasattr(args, "target_fps") and args.target_fps:
        cfg = replace(cfg, perf_target_fps=float(args.target_fps))

    if hasattr(args, "warmup_frames") and args.warmup_frames is not None:
        cfg = replace(cfg, perf_warmup_frames=max(0, int(args.warmup_frames)))

    if hasattr(args, "frames") and args.frames:
        cfg = replace(cfg, perf_sample_frames=max(1, int(args.frames)))

    if hasattr(args, "sync_vision") and args.sync_vision:
        cfg = replace(cfg, vision_async_enabled=False)

    if hasattr(args, "vision_max_age_ms") and args.vision_max_age_ms:
        cfg = replace(cfg, vision_async_max_result_age_ms=max(1.0, float(args.vision_max_age_ms)))

    if hasattr(args, "vision_workers") and args.vision_workers:
        cfg = replace(cfg, vision_async_workers=max(1, int(args.vision_workers)))

    if hasattr(args, "vision_max_pending") and args.vision_max_pending:
        cfg = replace(cfg, vision_async_max_pending_jobs=max(1, int(args.vision_max_pending)))

    if hasattr(args, "observer_off") and args.observer_off:
        cfg = replace(cfg, observer_enabled=False)

    if hasattr(args, "observer_event_queue") and args.observer_event_queue:
        cfg = replace(cfg, observer_event_queue_size=max(1, int(args.observer_event_queue)))

    if hasattr(args, "observer_image_queue") and args.observer_image_queue:
        cfg = replace(cfg, observer_image_queue_size=max(1, int(args.observer_image_queue)))

    if hasattr(args, "observer_batch_size") and args.observer_batch_size:
        cfg = replace(cfg, observer_event_batch_size=max(1, int(args.observer_batch_size)))

    if hasattr(args, "observer_flush_ms") and args.observer_flush_ms:
        cfg = replace(cfg, observer_flush_interval_ms=max(10, int(args.observer_flush_ms)))

    if hasattr(args, "observer_sample_fps") and float(args.observer_sample_fps) >= 0.0:
        cfg = replace(cfg, observer_full_frame_sample_fps=max(0.0, float(args.observer_sample_fps)))

    if hasattr(args, "observer_high_threat_min_danger") and args.observer_high_threat_min_danger:
        cfg = replace(cfg, observer_high_threat_min_danger=max(1, int(args.observer_high_threat_min_danger)))

    if hasattr(args, "observer_shadow_off") and args.observer_shadow_off:
        cfg = replace(cfg, observer_shadow_enabled=False)

    if hasattr(args, "observer_shadow_min_confidence") and float(args.observer_shadow_min_confidence) >= 0.0:
        cfg = replace(cfg, observer_shadow_min_confidence=float(args.observer_shadow_min_confidence))

    if hasattr(args, "observer_shadow_include_loading") and args.observer_shadow_include_loading:
        cfg = replace(cfg, observer_shadow_include_loading=True)

    if hasattr(args, "chat_commands_off") and args.chat_commands_off:
        cfg = replace(cfg, chat_commands_enabled=False)

    if hasattr(args, "chat_command_prefix") and str(args.chat_command_prefix).strip():
        cfg = replace(cfg, chat_command_prefix=str(args.chat_command_prefix).strip())

    if hasattr(args, "chat_command_senders") and str(args.chat_command_senders).strip():
        sender_tokens = tuple(
            token.strip()
            for token in str(args.chat_command_senders).split(",")
            if token.strip()
        )
        cfg = replace(cfg, chat_command_allowed_senders=sender_tokens)

    if hasattr(args, "chat_command_require_sender") and args.chat_command_require_sender:
        cfg = replace(cfg, chat_command_require_sender=True)

    if hasattr(args, "chat_command_allow_no_prefix") and args.chat_command_allow_no_prefix:
        cfg = replace(cfg, chat_command_allow_no_prefix=True)

    if hasattr(args, "pause_hotkey_off") and args.pause_hotkey_off:
        cfg = replace(cfg, pause_hotkey_enabled=False)

    if hasattr(args, "pause_hotkey_debounce_ms") and float(args.pause_hotkey_debounce_ms) >= 0.0:
        cfg = replace(cfg, pause_hotkey_debounce_s=max(0.0, float(args.pause_hotkey_debounce_ms) / 1000.0))

    if hasattr(args, "profile") and args.profile:
        requested = str(args.profile).strip()
        if requested not in cfg.available_profiles():
            available = ", ".join(cfg.available_profiles())
            raise ValueError(f"Unknown profile '{requested}'. Available profiles: {available}")
        cfg = replace(cfg, active_profile=requested)
    if cfg.vision_async_max_pending_jobs < cfg.vision_async_workers:
        cfg = replace(cfg, vision_async_max_pending_jobs=cfg.vision_async_workers)

    if cfg.observer_drop_policy not in {"drop_oldest", "drop_new"}:
        cfg = replace(cfg, observer_drop_policy="drop_oldest")

    if cfg.observer_event_batch_size > cfg.observer_event_queue_size:
        cfg = replace(cfg, observer_event_batch_size=cfg.observer_event_queue_size)

    if cfg.observer_shadow_min_confidence < 0.0:
        cfg = replace(cfg, observer_shadow_min_confidence=0.0)

    if cfg.observer_shadow_min_confidence > 1.0:
        cfg = replace(cfg, observer_shadow_min_confidence=1.0)

    if cfg.chat_command_poll_interval_s < 0.05:
        cfg = replace(cfg, chat_command_poll_interval_s=0.05)

    if cfg.chat_command_dedupe_window_s < 0.0:
        cfg = replace(cfg, chat_command_dedupe_window_s=0.0)

    if cfg.chat_command_max_lines < 1:
        cfg = replace(cfg, chat_command_max_lines=1)

    if cfg.chat_command_max_actions_per_poll < 1:
        cfg = replace(cfg, chat_command_max_actions_per_poll=1)

    if cfg.chat_command_ocr_confidence_threshold < 0.0:
        cfg = replace(cfg, chat_command_ocr_confidence_threshold=0.0)

    if cfg.chat_command_ocr_confidence_threshold > 100.0:
        cfg = replace(cfg, chat_command_ocr_confidence_threshold=100.0)

    if cfg.pause_hotkey_debounce_s < 0.0:
        cfg = replace(cfg, pause_hotkey_debounce_s=0.0)

    return cfg


def prepare_window_and_vision(config: RuntimeConfig, logger):
    """Prepare window and vision.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        capture_region: Local variable for capture region used in this routine.
        vision: Local variable for vision used in this routine.
        window_manager: Local variable for window manager used in this routine.
        window_rect: Local variable for window rect used in this routine.

    Returns:
        A computed value produced by the routine.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    window_manager = GameWindowManager(config, logger=logger)
    window_rect = window_manager.locate_and_prepare_window()
    capture_region = window_manager.build_automap_region(window_rect)
    vision = Vision(config, capture_region)

    logger.info("Capture region set to %s", capture_region)
    return window_manager, window_rect, vision


def prepare_synthetic_vision(config: RuntimeConfig, logger, image_path: str):
    """Prepare synthetic vision.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.
        image_path: Parameter containing a filesystem location.

    Local Variables:
        frame_seed: Local variable representing image frame data for vision processing.
        region: Local variable for region used in this routine.
        source: Local variable for source used in this routine.
        vision: Local variable for vision used in this routine.

    Returns:
        A computed value produced by the routine.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    region = {
        "left": 0,
        "top": 0,
        "width": int(config.automap_width),
        "height": int(config.automap_height),
    }
    vision = Vision(config, region)

    if image_path:
        source = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if source is None:
            raise RuntimeError(f"Unable to read synthetic image: {image_path}")
        frame_seed = source
        logger.info("Using synthetic frame image: %s", image_path)
    else:
        frame_seed = np.zeros((region["height"], region["width"], 3), dtype=np.uint8)
        cv2.putText(
            frame_seed,
            "PERF_SYNTHETIC",
            (20, max(30, region["height"] // 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        logger.info("Using generated synthetic frame source")

    def provider() -> np.ndarray:
        """Provider.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `np.ndarray`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return frame_seed.copy()

    return vision, provider


def _build_runtime_components(config: RuntimeConfig, logger):
    """Internal helper to build runtime components.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        combat_routine: Local variable for combat routine used in this routine.
        commands: Local variable for commands used in this routine.
        controller: Local variable for controller used in this routine.
        enemy_tracker: Local variable for enemy tracker used in this routine.
        gameplay_planner: Local variable for gameplay planner used in this routine.
        gameplay_scanner: Local variable for gameplay scanner used in this routine.
        limiter: Local variable for limiter used in this routine.
        pickit_db: Local variable for pickit db used in this routine.
        policy: Local variable for policy used in this routine.
        state_manager: Local variable carrying runtime state information.

    Returns:
        A computed value produced by the routine.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    controller = Controller(config)
    state_manager = StateManager(level_stabilize_time=config.level_stabilize_time)
    policy = RulePolicy(config)
    commands = CommandModule()
    chat_processor = ChatCommandProcessor(config=config, logger=logger)
    pause_hotkey_monitor = PauseHotkeyMonitor(
        enabled=config.pause_hotkey_enabled,
        debounce_seconds=config.pause_hotkey_debounce_s,
    )
    limiter = FPSLimiter(fps=config.fps)

    enemy_tracker = EnemyTracker(
        match_distance_px=config.enemy_track_match_distance_px,
        max_lost_frames=config.enemy_track_max_lost_frames,
    )
    combat_routine = CombatRoutine(
        engage_range_px=config.effective_combat_engage_range_px,
        close_range_px=config.effective_combat_close_range_px,
        spell_slot=config.effective_combat_spell_slot,
        prefer_combat=config.effective_prefer_combat,
        spell_rotation=config.effective_combat_spell_rotation,
        class_name=config.effective_class_name,
        necromancer_config=config.effective_necromancer_config,
    )

    pickit_db = PickitDatabase.load(config.pickit_db_path, logger=logger)
    gameplay_scanner = GameplayScanner(config=config, pickit_db=pickit_db)
    gameplay_planner = GameplayActionPlanner(config=config)

    return (
        controller,
        state_manager,
        policy,
        commands,
        chat_processor,
        pause_hotkey_monitor,
        limiter,
        enemy_tracker,
        combat_routine,
        gameplay_scanner,
        gameplay_planner,
    )


def _process_frame_for_vision(
    vision: Vision,
    frame: np.ndarray,
    level_number: int,
    enable_combat_stub: bool,
    enemy_tracker: EnemyTracker,
    gameplay_scanner: GameplayScanner,
) -> GameState:
    """Internal helper to process frame for vision.

    Parameters:
        vision: Parameter for vision used in this routine.
        frame: Parameter representing image frame data for vision processing.
        level_number: Parameter for level number used in this routine.
        enable_combat_stub: Parameter for enable combat stub used in this routine.
        enemy_tracker: Parameter for enemy tracker used in this routine.
        gameplay_scanner: Parameter for gameplay scanner used in this routine.

    Local Variables:
        enemy_detections: Local variable for enemy detections used in this routine.
        enemy_tracks: Local variable for enemy tracks used in this routine.
        state: Local variable carrying runtime state information.

    Returns:
        A value matching the annotated return type `GameState`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    enemy_detections = []
    enemy_tracks = []
    if enable_combat_stub:
        enemy_detections = vision.scan_enemies(frame)
        enemy_tracks = vision.track_enemies(enemy_detections, enemy_tracker)

    state = vision.extract_game_state(
        frame,
        level_number,
        enemy_detections=enemy_detections,
        enemy_tracks=enemy_tracks,
        combat_state="idle",
    )

    return gameplay_scanner.enrich_state(vision, frame, state)


def _fallback_state_from_frame(vision: Vision, frame: np.ndarray, level_number: int) -> GameState:
    """Build a minimal safe state when no fresh async vision result is available."""
    player_position = vision.get_player_position(frame)
    return GameState(
        automap_matrix=frame,
        teammate_detections=[],
        player_position=player_position,
        relative_vectors=[],
        enemy_detections=[],
        enemy_tracks=[],
        combat_state="vision_fallback",
        level_number=level_number,
        loading=vision.is_loading(frame),
    )



def _max_danger_priority_from_state(game_state: GameState) -> int:
    """Extract the highest danger-priority value from active enemies."""
    active_track_priorities = [
        int(track.danger_priority)
        for track in game_state.enemy_tracks
        if int(track.lost_frames) == 0
    ]
    if active_track_priorities:
        return max(active_track_priorities)

    detection_priorities = [int(detection.danger_priority) for detection in game_state.enemy_detections]
    if detection_priorities:
        return max(detection_priorities)

    return 0


def _max_target_priority_score_from_state(game_state: GameState) -> int:
    """Extract highest target-priority score from active tracks/detections."""
    active_track_scores = [
        int(track.target_priority_score)
        for track in game_state.enemy_tracks
        if int(track.lost_frames) == 0
    ]
    if active_track_scores:
        return max(active_track_scores)

    detection_scores = [int(detection.target_priority_score) for detection in game_state.enemy_detections]
    if detection_scores:
        return max(detection_scores)

    return 0


def _build_observer_event(
    config: RuntimeConfig,
    frame_id: int,
    loop_start_monotonic: float,
    wall_timestamp: float,
    game_state: GameState,
    lifecycle_state: str,
    action: Optional[Action],
    action_source: str,
    combat_decision: Optional[CombatDecision],
    vision_mode: str,
    used_fallback_state: bool,
    health_ratio: float,
    mana_ratio: float,
    stage_timings_ms: Dict[str, float],
) -> ObservationEvent:
    """Build a normalized observer event payload from runtime frame context."""
    max_danger_priority = _max_danger_priority_from_state(game_state)
    max_target_priority_score = _max_target_priority_score_from_state(game_state)

    threat_band = classify_threat_band(max_danger_priority)
    party_size_band = classify_party_size_band(len(game_state.teammate_detections))

    scenario_tags = sanitize_scenario_tags(
        {
            "profile": config.active_profile,
            "class_name": config.effective_class_name,
            "level_number": int(game_state.level_number),
            "party_size_band": party_size_band,
            "threat_band": threat_band,
            "combat_mode": str(game_state.combat_state),
            "vision_mode": str(vision_mode),
            "fallback_state": "true" if used_fallback_state else "false",
            "dry_run": "true" if config.dry_run else "false",
        }
    )

    event_flags = []
    if used_fallback_state:
        event_flags.append("vision_fallback")
    if game_state.loading:
        event_flags.append("loading")
    if max_danger_priority >= int(config.observer_high_threat_min_danger):
        event_flags.append("high_threat")
    if action is None:
        event_flags.append("no_action")

    action_click_target = None if action is None else action.click_target
    action_cast_spell = None if action is None else action.cast_spell
    action_hold_move = None if action is None else action.hold_move
    action_stop = False if action is None else bool(action.stop)
    action_reason = "" if action is None else str(action.reason)

    combat_mode = "" if combat_decision is None else str(combat_decision.mode)
    combat_target_track_id = None if combat_decision is None else combat_decision.target_track_id
    combat_target_priority_score = 0 if combat_decision is None else int(combat_decision.target_priority_score)

    return ObservationEvent(
        schema_version=max(1, int(config.observer_schema_version)),
        frame_id=int(frame_id),
        monotonic_timestamp=float(loop_start_monotonic),
        wall_timestamp=float(wall_timestamp),
        lifecycle_state=str(lifecycle_state),
        profile_name=str(config.active_profile),
        class_name=str(config.effective_class_name),
        level_number=int(game_state.level_number),
        vision_mode=str(vision_mode),
        used_fallback_state=bool(used_fallback_state),
        player_position=(int(game_state.player_position[0]), int(game_state.player_position[1])),
        teammate_count=len(game_state.teammate_detections),
        enemy_detection_count=len(game_state.enemy_detections),
        enemy_track_count=len(game_state.enemy_tracks),
        ground_item_count=len(game_state.ground_items),
        gold_item_count=len(game_state.gold_items),
        pickit_match_count=len(game_state.pickit_matches),
        health_ratio=float(health_ratio),
        mana_ratio=float(mana_ratio),
        max_danger_priority=int(max_danger_priority),
        max_target_priority_score=int(max_target_priority_score),
        threat_band=str(threat_band),
        party_size_band=str(party_size_band),
        action_source=str(action_source),
        action_reason=str(action_reason),
        action_click_target=action_click_target,
        action_cast_spell=action_cast_spell,
        action_hold_move=action_hold_move,
        action_stop=bool(action_stop),
        combat_mode=str(combat_mode),
        combat_target_track_id=combat_target_track_id,
        combat_target_priority_score=int(combat_target_priority_score),
        scenario_tags=scenario_tags,
        stage_timings_ms={
            str(stage_name): float(stage_value)
            for stage_name, stage_value in stage_timings_ms.items()
        },
        flags=tuple(event_flags),
    )
def _run_frame_loop(
    config: RuntimeConfig,
    logger,
    vision: Vision,
    frame_provider: FrameProvider,
    frame_limit: int = 0,
    monitor: Optional[PerformanceMonitor] = None,
):
    """Internal helper to run frame loop.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.
        vision: Parameter for vision used in this routine.
        frame_provider: Parameter representing image frame data for vision processing.
        frame_limit: Parameter representing image frame data for vision processing.
        monitor: Parameter for monitor used in this routine.

    Local Variables:
        action: Local variable for action used in this routine.
        async_runner: Local variable for async runner used in this routine.
        async_stats: Local variable for async stats used in this routine.
        attempted: Local variable for attempted used in this routine.
        capture_ms: Local variable storing a duration value in milliseconds.
        combat_decision: Local variable for combat decision used in this routine.
        combat_routine: Local variable for combat routine used in this routine.
        commands: Local variable for commands used in this routine.
        control_ms: Local variable storing a duration value in milliseconds.
        controller: Local variable for controller used in this routine.
        decision_ms: Local variable storing a duration value in milliseconds.
        drop_rate: Local variable for drop rate used in this routine.
        enemy_tracker: Local variable for enemy tracker used in this routine.
        frame: Local variable representing image frame data for vision processing.
        frame_count: Local variable tracking how many items are present or processed.
        game_state: Local variable carrying runtime state information.
        gameplay_planner: Local variable for gameplay planner used in this routine.
        gameplay_scanner: Local variable for gameplay scanner used in this routine.
        health_ratio: Local variable for health ratio used in this routine.
        level_number: Local variable for level number used in this routine.
        lifecycle: Local variable for lifecycle used in this routine.
        limiter: Local variable for limiter used in this routine.
        loop_start: Local variable for loop start used in this routine.
        mana_ratio: Local variable for mana ratio used in this routine.
        plan_stats: Local variable for plan stats used in this routine.
        policy: Local variable for policy used in this routine.
        resource: Local variable for resource used in this routine.
        scan_stats: Local variable for scan stats used in this routine.
        sleep_ms: Local variable storing a duration value in milliseconds.
        snapshot: Local variable for snapshot used in this routine.
        stage_start: Local variable for stage start used in this routine.
        state_manager: Local variable carrying runtime state information.
        state_ms: Local variable storing a duration value in milliseconds.
        total_ms: Local variable storing a duration value in milliseconds.
        vision_mode: Local variable for vision mode used in this routine.
        vision_ms: Local variable storing a duration value in milliseconds.
        worker_error: Local variable carrying error details for handling or reporting.

    Returns:
        None.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    (
        controller,
        state_manager,
        policy,
        commands,
        chat_processor,
        pause_hotkey_monitor,
        limiter,
        enemy_tracker,
        combat_routine,
        gameplay_scanner,
        gameplay_planner,
    ) = _build_runtime_components(config, logger)

    level_number = 1
    frame_count = 0
    hotkey_toggle_count = 0
    vision_mode = "async" if config.vision_async_enabled else "sync"

    logger.info(
        "Loop starting (profile=%s, class=%s, follow_radius=%d, dry_run=%s, combat_stub=%s, fps=%d, vision_mode=%s, vision_max_age_ms=%.1f, vision_workers=%d, vision_max_pending=%d, observer=%s, observer_event_queue=%d, observer_batch=%d)",
        config.active_profile,
        config.effective_class_name,
        config.effective_follow_radius_px,
        config.dry_run,
        config.enable_combat_stub,
        config.fps,
        vision_mode,
        config.vision_async_max_result_age_ms,
        config.vision_async_workers,
        config.vision_async_max_pending_jobs,
        config.observer_enabled,
        config.observer_event_queue_size,
        config.observer_event_batch_size,
    )

    if monitor is not None:
        monitor.annotate("vision_mode", vision_mode)
        monitor.annotate("vision_max_age_ms", float(config.vision_async_max_result_age_ms))
        monitor.annotate("vision_async_workers", int(config.vision_async_workers))
        monitor.annotate("vision_async_max_pending_jobs", int(config.vision_async_max_pending_jobs))
        monitor.annotate("observer_enabled", bool(config.observer_enabled))
        monitor.annotate("observer_event_queue_size", int(config.observer_event_queue_size))
        monitor.annotate("observer_event_batch_size", int(config.observer_event_batch_size))
        monitor.annotate("observer_flush_interval_ms", int(config.observer_flush_interval_ms))
        monitor.annotate("observer_full_frame_sample_fps", float(config.observer_full_frame_sample_fps))
        monitor.annotate("observer_shadow_enabled", bool(config.observer_shadow_enabled))
        monitor.annotate("observer_shadow_min_confidence", float(config.observer_shadow_min_confidence))
        monitor.annotate("observer_shadow_include_loading", bool(config.observer_shadow_include_loading))
        monitor.annotate("chat_commands_enabled", bool(config.chat_commands_enabled))
        monitor.annotate("chat_command_prefix", str(config.chat_command_prefix))
        monitor.annotate("chat_command_poll_interval_s", float(config.chat_command_poll_interval_s))
        monitor.annotate("chat_command_require_sender", bool(config.chat_command_require_sender))
        monitor.annotate("chat_command_allowed_sender_count", int(len(config.chat_command_allowed_senders)))
        monitor.annotate("pause_hotkey_enabled", bool(config.pause_hotkey_enabled))
        monitor.annotate("pause_hotkey_debounce_s", float(config.pause_hotkey_debounce_s))

    async_runner: Optional[AsyncVisionRunner] = None
    if config.vision_async_enabled:
        async_runner = AsyncVisionRunner(
            processor=lambda worker_frame, worker_level: _process_frame_for_vision(
                vision,
                worker_frame,
                worker_level,
                config.enable_combat_stub,
                enemy_tracker,
                gameplay_scanner,
            ),
            max_result_age_ms=config.vision_async_max_result_age_ms,
            max_workers=config.vision_async_workers,
            max_pending_jobs=config.vision_async_max_pending_jobs,
        )

    if monitor is not None and async_runner is None:
        monitor.annotate("vision_async_submitted", 0)
        monitor.annotate("vision_async_completed", 0)
        monitor.annotate("vision_async_dropped", 0)
        monitor.annotate("vision_async_inflight", False)
        monitor.annotate("vision_async_inflight_count", 0)
        monitor.annotate("vision_async_dropped_stale", 0)
        monitor.annotate("vision_async_dropped_backpressure", 0)
        monitor.annotate("vision_async_drop_rate", 0.0)

    observer: Optional[ObserverWorker] = None
    if config.observer_enabled:
        try:
            observer = ObserverWorker(config=config, logger=logger)
            observer.start()
            logger.info(
                "Observer started (drop_policy=%s event_queue=%d batch=%d flush_ms=%d frame_sample_fps=%.2f shadow=%s shadow_min_conf=%.2f include_loading=%s)",
                config.observer_drop_policy,
                config.observer_event_queue_size,
                config.observer_event_batch_size,
                config.observer_flush_interval_ms,
                config.observer_full_frame_sample_fps,
                config.observer_shadow_enabled,
                config.observer_shadow_min_confidence,
                config.observer_shadow_include_loading,
            )
        except Exception as observer_start_error:
            observer = None
            logger.warning(
                "Observer startup failed; continuing without observer capture: %s",
                observer_start_error,
            )

    if monitor is not None and observer is None:
        monitor.annotate("observer_submitted_events", 0)
        monitor.annotate("observer_written_events", 0)
        monitor.annotate("observer_dropped_events", 0)
        monitor.annotate("observer_event_queue_max_depth", 0)
        monitor.annotate("observer_submitted_images", 0)
        monitor.annotate("observer_written_images", 0)
        monitor.annotate("observer_dropped_images", 0)
        monitor.annotate("observer_image_queue_max_depth", 0)
        monitor.annotate("observer_write_errors", 0)
        monitor.annotate("observer_coverage_total_events", 0)
        monitor.annotate("observer_coverage_unique_buckets", 0)
        monitor.annotate("observer_shadow_seen_events", 0)
        monitor.annotate("observer_shadow_evaluated_events", 0)
        monitor.annotate("observer_shadow_agreement_count", 0)
        monitor.annotate("observer_shadow_disagreement_count", 0)
        monitor.annotate("observer_shadow_agreement_rate", 0.0)
        monitor.annotate("observer_shadow_skipped_loading", 0)
        monitor.annotate("observer_shadow_skipped_low_confidence", 0)
        monitor.annotate("observer_shadow_metrics_path", "")

    try:
        while True:
            loop_start = time.monotonic()

            stage_start = time.monotonic()
            frame = frame_provider()
            capture_ms = (time.monotonic() - stage_start) * 1000.0

            used_fallback_state = False
            combat_decision: Optional[CombatDecision] = None
            action_source = "none"

            stage_start = time.monotonic()
            if async_runner is None:
                game_state = _process_frame_for_vision(
                    vision,
                    frame,
                    level_number,
                    config.enable_combat_stub,
                    enemy_tracker,
                    gameplay_scanner,
                )
            else:
                async_runner.submit(frame, level_number)

                worker_error = async_runner.pop_error()
                if worker_error is not None:
                    logger.warning("Async vision worker error: %s", worker_error)

                snapshot = async_runner.latest()
                if snapshot is None:
                    used_fallback_state = True
                    game_state = _fallback_state_from_frame(vision, frame, level_number)
                else:
                    game_state = snapshot.state

            vision_ms = (time.monotonic() - stage_start) * 1000.0

            stage_start = time.monotonic()
            lifecycle = state_manager.update_state(game_state)
            state_ms = (time.monotonic() - stage_start) * 1000.0

            stage_start = time.monotonic()

            forced_hotkey_action: Optional[Action] = None
            if pause_hotkey_monitor.poll(now_monotonic=loop_start):
                next_paused_state = not commands.is_paused()
                commands.set_paused(next_paused_state)
                hotkey_toggle_count += 1

                if next_paused_state:
                    dropped_pending = commands.clear_pending_commands()
                    forced_hotkey_action = Action(stop=True, reason="hotkey_pause_toggle_on")
                    logger.info(
                        "Pause enabled via Ctrl+Space (dropped_pending_commands=%d)",
                        dropped_pending,
                    )
                else:
                    forced_hotkey_action = Action(hold_move=False, reason="hotkey_pause_toggle_off")
                    logger.info("Pause disabled via Ctrl+Space")

            chat_events = chat_processor.poll_and_apply(
                vision=vision,
                frame=frame,
                commands=commands,
                now_monotonic=loop_start,
            )
            if config.debug and chat_events:
                for chat_event in chat_events:
                    logger.debug(
                        "chat_cmd sender=%s cmd=%s arg=%s accepted=%s reason=%s conf=%.1f",
                        chat_event.sender,
                        chat_event.command,
                        chat_event.argument,
                        chat_event.accepted,
                        chat_event.reason,
                        chat_event.confidence,
                    )

            action = forced_hotkey_action
            if action is not None:
                action_source = "pause_hotkey_toggle"

            if action is None and commands.is_paused():
                action = Action(stop=True, reason="paused_state_hold")
                action_source = "paused_state"

            if action is None:
                action = commands.get_next()
                if action is not None:
                    action_source = "command_queue"
            potion_enabled = commands.is_potion_enabled(config.enable_belt_management)
            pickup_enabled = commands.is_pickup_enabled(config.enable_item_pickup or config.enable_gold_pickup)
            combat_enabled = commands.is_combat_enabled(config.enable_combat_stub)

            if action is None:
                action = gameplay_planner.decide(
                    game_state,
                    allow_potions=potion_enabled,
                    allow_pickups=pickup_enabled,
                )
                if action is not None:
                    action_source = "gameplay_planner"

            if action is None and combat_enabled and config.effective_prefer_combat:
                combat_decision = combat_routine.decide(game_state)
                if combat_decision is not None:
                    action = combat_decision.action
                    action_source = "combat_routine_primary"
                    game_state.combat_state = combat_decision.mode
                elif game_state.enemy_tracks:
                    game_state.combat_state = "tracking_only_stub"

            if action is None:
                action = policy.decide(game_state)
                if action is not None:
                    action_source = "rule_policy"

            if (
                action is not None
                and action.reason == "no_teammates"
                and combat_enabled
                and not config.effective_prefer_combat
            ):
                combat_decision = combat_routine.decide(game_state)
                if combat_decision is not None:
                    action = combat_decision.action
                    action_source = "combat_routine_recovery"
                    game_state.combat_state = combat_decision.mode

            if action is None:
                action = Action(reason="idle_no_action")
                action_source = "idle_fallback"

            decision_ms = (time.monotonic() - stage_start) * 1000.0

            stage_start = time.monotonic()
            controller.execute_action(action)
            control_ms = (time.monotonic() - stage_start) * 1000.0

            stage_start = time.monotonic()
            limiter.wait()
            sleep_ms = (time.monotonic() - stage_start) * 1000.0

            total_ms = (time.monotonic() - loop_start) * 1000.0

            resource_status = game_state.resource_status
            health_ratio = -1.0 if resource_status is None else float(resource_status.health_ratio)
            mana_ratio = -1.0 if resource_status is None else float(resource_status.mana_ratio)

            if monitor is not None:
                monitor.record(
                    timing_from_stages(
                        capture_ms=capture_ms,
                        vision_ms=vision_ms,
                        state_ms=state_ms,
                        decision_ms=decision_ms,
                        control_ms=control_ms,
                        sleep_ms=sleep_ms,
                        total_ms=total_ms,
                    )
                )

            if observer is not None:
                observer_event = _build_observer_event(
                    config=config,
                    frame_id=frame_count + 1,
                    loop_start_monotonic=loop_start,
                    wall_timestamp=time.time(),
                    game_state=game_state,
                    lifecycle_state=lifecycle.value,
                    action=action,
                    action_source=action_source,
                    combat_decision=combat_decision,
                    vision_mode=vision_mode,
                    used_fallback_state=used_fallback_state,
                    health_ratio=health_ratio,
                    mana_ratio=mana_ratio,
                    stage_timings_ms={
                        "capture": capture_ms,
                        "vision": vision_ms,
                        "state": state_ms,
                        "decision": decision_ms,
                        "control": control_ms,
                        "sleep": sleep_ms,
                        "total": total_ms,
                    },
                )
                observer.publish_event(observer_event)

                sampled_high_threat = observer.maybe_publish_high_threat_frame_sample(
                    frame=frame,
                    frame_id=frame_count + 1,
                    scenario_tags=observer_event.scenario_tags,
                    max_danger_priority=observer_event.max_danger_priority,
                    wall_timestamp=observer_event.wall_timestamp,
                )
                if not sampled_high_threat:
                    observer.maybe_publish_periodic_frame_sample(
                        frame=frame,
                        frame_id=frame_count + 1,
                        scenario_tags=observer_event.scenario_tags,
                        wall_timestamp=observer_event.wall_timestamp,
                    )

            if config.debug:
                if async_runner is not None and frame_count % max(1, config.fps) == 0:
                    async_stats = async_runner.stats()
                    logger.debug(
                        "vision_async submitted=%d completed=%d dropped=%d stale=%d backpressure=%d inflight=%s inflight_count=%d",
                        async_stats.submitted,
                        async_stats.completed,
                        async_stats.dropped,
                        async_stats.dropped_stale,
                        async_stats.dropped_backpressure,
                        async_stats.inflight,
                        async_stats.inflight_count,
                    )

                if observer is not None and frame_count % max(1, config.fps) == 0:
                    observer_stats = observer.stats()
                    logger.debug(
                        "observer submitted_events=%d written_events=%d dropped_events=%d event_queue=%d submitted_images=%d written_images=%d dropped_images=%d image_queue=%d write_errors=%d shadow_eval=%d shadow_rate=%.3f",
                        observer_stats.submitted_events,
                        observer_stats.written_events,
                        observer_stats.dropped_events,
                        observer_stats.event_queue_depth,
                        observer_stats.submitted_images,
                        observer_stats.written_images,
                        observer_stats.dropped_images,
                        observer_stats.image_queue_depth,
                        observer_stats.write_errors,
                        observer_stats.shadow_evaluated_events,
                        observer_stats.shadow_agreement_rate,
                    )

                if frame_count % max(1, config.fps) == 0:
                    chat_stats = chat_processor.stats()
                    logger.debug(
                        "chat_cmd polls=%d scanned=%d parsed=%d accepted=%d rejected=%d dup=%d low_conf=%d paused=%s combat=%s pickup=%s potion=%s",
                        chat_stats.poll_count,
                        chat_stats.scanned_lines,
                        chat_stats.parsed_commands,
                        chat_stats.accepted_commands,
                        chat_stats.rejected_commands,
                        chat_stats.duplicate_drops,
                        chat_stats.low_confidence_drops,
                        commands.is_paused(),
                        commands.is_combat_enabled(config.enable_combat_stub),
                        commands.is_pickup_enabled(config.enable_item_pickup or config.enable_gold_pickup),
                        commands.is_potion_enabled(config.enable_belt_management),
                    )

                logger.debug(
                    "state=%s teammates=%s enemies=%d tracks=%d loot=%d pickit=%d health=%.2f mana=%.2f combat=%s action=%s reason=%s frame_ms=%.2f",
                    lifecycle.value,
                    game_state.teammate_positions,
                    len(game_state.enemy_detections),
                    len(game_state.enemy_tracks),
                    len(game_state.ground_items),
                    len(game_state.pickit_matches),
                    health_ratio,
                    mana_ratio,
                    game_state.combat_state,
                    None if action is None else action.click_target,
                    None if action is None else action.reason,
                    total_ms,
                )

            frame_count += 1

            if frame_limit and frame_count >= frame_limit:
                logger.info("Reached frame limit: %d", frame_limit)
                break
    finally:
        if monitor is not None:
            scan_stats = gameplay_scanner.stats()
            plan_stats = gameplay_planner.stats()
            monitor.annotate("gameplay_resource_scans", scan_stats.resource_scans)
            monitor.annotate("gameplay_belt_scans", scan_stats.belt_scans)
            monitor.annotate("gameplay_ground_scans", scan_stats.ground_scans)
            monitor.annotate("gameplay_pickit_matches", scan_stats.pickit_matches)
            monitor.annotate("gameplay_buff_checks", scan_stats.buff_checks)
            monitor.annotate("gameplay_merc_checks", scan_stats.merc_checks)
            monitor.annotate("gameplay_inventory_checks", scan_stats.inventory_checks)
            monitor.annotate("gameplay_potion_actions", plan_stats.potion_actions)
            monitor.annotate("gameplay_pickup_actions", plan_stats.pickup_actions)
            chat_stats = chat_processor.stats()
            monitor.annotate("chat_command_poll_count", chat_stats.poll_count)
            monitor.annotate("chat_command_scanned_lines", chat_stats.scanned_lines)
            monitor.annotate("chat_command_parsed", chat_stats.parsed_commands)
            monitor.annotate("chat_command_accepted", chat_stats.accepted_commands)
            monitor.annotate("chat_command_rejected", chat_stats.rejected_commands)
            monitor.annotate("chat_command_duplicates", chat_stats.duplicate_drops)
            monitor.annotate("chat_command_low_confidence_drops", chat_stats.low_confidence_drops)
            monitor.annotate("chat_command_paused", commands.is_paused())
            monitor.annotate("chat_command_combat_enabled", commands.is_combat_enabled(config.enable_combat_stub))
            monitor.annotate("chat_command_pickup_enabled", commands.is_pickup_enabled(config.enable_item_pickup or config.enable_gold_pickup))
            monitor.annotate("chat_command_potion_enabled", commands.is_potion_enabled(config.enable_belt_management))
            monitor.annotate("pause_hotkey_toggle_count", int(hotkey_toggle_count))


        chat_stats = chat_processor.stats()
        logger.info(
            "Chat command stats | polls=%d scanned=%d parsed=%d accepted=%d rejected=%d dup=%d low_conf=%d paused=%s combat=%s pickup=%s potion=%s",
            chat_stats.poll_count,
            chat_stats.scanned_lines,
            chat_stats.parsed_commands,
            chat_stats.accepted_commands,
            chat_stats.rejected_commands,
            chat_stats.duplicate_drops,
            chat_stats.low_confidence_drops,
            commands.is_paused(),
            commands.is_combat_enabled(config.enable_combat_stub),
            commands.is_pickup_enabled(config.enable_item_pickup or config.enable_gold_pickup),
            commands.is_potion_enabled(config.enable_belt_management),
        )
        logger.info("Pause hotkey toggles this run: %d", hotkey_toggle_count)

        if async_runner is not None:
            async_stats = async_runner.stats()
            if monitor is not None:
                attempted = async_stats.submitted + async_stats.dropped
                drop_rate = (async_stats.dropped / attempted) if attempted > 0 else 0.0
                monitor.annotate("vision_async_submitted", async_stats.submitted)
                monitor.annotate("vision_async_completed", async_stats.completed)
                monitor.annotate("vision_async_dropped", async_stats.dropped)
                monitor.annotate("vision_async_inflight", async_stats.inflight)
                monitor.annotate("vision_async_inflight_count", async_stats.inflight_count)
                monitor.annotate("vision_async_dropped_stale", async_stats.dropped_stale)
                monitor.annotate("vision_async_dropped_backpressure", async_stats.dropped_backpressure)
                monitor.annotate("vision_async_drop_rate", round(drop_rate, 6))
            async_runner.close()

        if observer is not None:
            observer_stats = observer.close()
            logger.info(
                "Observer final stats | events submitted=%d written=%d dropped=%d queue_max=%d images submitted=%d written=%d dropped=%d image_queue_max=%d write_errors=%d coverage_events=%d coverage_buckets=%d shadow_seen=%d shadow_evaluated=%d shadow_agree=%d shadow_disagree=%d shadow_rate=%.3f",
                observer_stats.submitted_events,
                observer_stats.written_events,
                observer_stats.dropped_events,
                observer_stats.event_queue_max_depth,
                observer_stats.submitted_images,
                observer_stats.written_images,
                observer_stats.dropped_images,
                observer_stats.image_queue_max_depth,
                observer_stats.write_errors,
                observer_stats.coverage_total_events,
                observer_stats.coverage_unique_buckets,
                observer_stats.shadow_seen_events,
                observer_stats.shadow_evaluated_events,
                observer_stats.shadow_agreement_count,
                observer_stats.shadow_disagreement_count,
                observer_stats.shadow_agreement_rate,
            )

            if monitor is not None:
                monitor.annotate("observer_submitted_events", observer_stats.submitted_events)
                monitor.annotate("observer_written_events", observer_stats.written_events)
                monitor.annotate("observer_dropped_events", observer_stats.dropped_events)
                monitor.annotate("observer_event_queue_max_depth", observer_stats.event_queue_max_depth)
                monitor.annotate("observer_submitted_images", observer_stats.submitted_images)
                monitor.annotate("observer_written_images", observer_stats.written_images)
                monitor.annotate("observer_dropped_images", observer_stats.dropped_images)
                monitor.annotate("observer_image_queue_max_depth", observer_stats.image_queue_max_depth)
                monitor.annotate("observer_write_errors", observer_stats.write_errors)
                monitor.annotate("observer_coverage_total_events", observer_stats.coverage_total_events)
                monitor.annotate("observer_coverage_unique_buckets", observer_stats.coverage_unique_buckets)
                monitor.annotate("observer_event_log_path", observer_stats.event_log_path)
                monitor.annotate("observer_coverage_path", observer_stats.coverage_path)
                monitor.annotate("observer_shadow_seen_events", observer_stats.shadow_seen_events)
                monitor.annotate("observer_shadow_evaluated_events", observer_stats.shadow_evaluated_events)
                monitor.annotate("observer_shadow_agreement_count", observer_stats.shadow_agreement_count)
                monitor.annotate("observer_shadow_disagreement_count", observer_stats.shadow_disagreement_count)
                monitor.annotate("observer_shadow_agreement_rate", observer_stats.shadow_agreement_rate)
                monitor.annotate("observer_shadow_skipped_loading", observer_stats.shadow_skipped_loading)
                monitor.annotate("observer_shadow_skipped_low_confidence", observer_stats.shadow_skipped_low_confidence)
                monitor.annotate("observer_shadow_metrics_path", observer_stats.shadow_metrics_path)

def run_loop(config: RuntimeConfig, logger):
    """Run loop.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        vision: Local variable for vision used in this routine.

    Returns:
        None.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    run_startup_checks(config, logger)
    _, _, vision = prepare_window_and_vision(config, logger)
    _run_frame_loop(config=config, logger=logger, vision=vision, frame_provider=vision.grab_frame, frame_limit=config.max_frames)



def run_center_window(config: RuntimeConfig, logger):
    """Run center window.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        region: Local variable for region used in this routine.
        window_manager: Local variable for window manager used in this routine.
        window_rect: Local variable for window rect used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    run_startup_checks(config, logger)
    window_manager, window_rect, _ = prepare_window_and_vision(config, logger)
    region = window_manager.build_automap_region(window_rect)
    logger.info("Window centered and ready. Automap region: %s", region)



def run_collect_ocr(config: RuntimeConfig, args: argparse.Namespace, logger):
    """Run collect ocr.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        args: Parameter for args used in this routine.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        collector: Local variable for collector used in this routine.
        output_dir: Local variable containing a filesystem location.
        summary: Local variable for summary used in this routine.
        vision: Local variable for vision used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    run_startup_checks(config, logger)

    _, _, vision = prepare_window_and_vision(config, logger)
    output_dir = Path(args.output_dir) if args.output_dir else config.ocr_dataset_raw_dir

    collector = OCRDatasetCollector(vision=vision, output_dir=output_dir, logger=logger)
    summary = collector.capture(sample_goal=args.samples, interval_seconds=args.interval)

    logger.info(
        "OCR collection complete: saved=%d output_dir=%s manifest=%s",
        summary.saved,
        summary.output_dir,
        summary.manifest_path,
    )




def run_ocr_bench(config: RuntimeConfig, args: argparse.Namespace, logger):
    """Run ocr bench.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        args: Parameter for args used in this routine.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        capture_ms: Local variable storing a duration value in milliseconds.
        explicit_output: Local variable for explicit output used in this routine.
        frame: Local variable representing image frame data for vision processing.
        frame_provider: Local variable representing image frame data for vision processing.
        ground_count: Local variable tracking how many items are present or processed.
        ground_max_labels: Local variable for ground max labels used in this routine.
        ground_ms: Local variable storing a duration value in milliseconds.
        limiter: Local variable for limiter used in this routine.
        mode: Local variable for mode used in this routine.
        monitor: Local variable for monitor used in this routine.
        report_path: Local variable containing a filesystem location.
        reporter: Local variable for reporter used in this routine.
        sample_idx: Local variable used as a position index while iterating.
        samples: Local variable for samples used in this routine.
        stage: Local variable for stage used in this routine.
        stage_start: Local variable for stage start used in this routine.
        stats: Local variable for stats used in this routine.
        summary: Local variable for summary used in this routine.
        teammate_count: Local variable tracking how many items are present or processed.
        teammate_ms: Local variable storing a duration value in milliseconds.
        total_ms: Local variable storing a duration value in milliseconds.
        total_start: Local variable for total start used in this routine.
        vision: Local variable for vision used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    run_startup_checks(config, logger)

    if args.synthetic:
        vision, frame_provider = prepare_synthetic_vision(config, logger, args.synthetic_image)
    else:
        _, _, vision = prepare_window_and_vision(config, logger)
        frame_provider = vision.grab_frame

    samples = max(1, int(args.samples))
    mode = str(args.mode)
    ground_max_labels = max(1, int(args.ground_max_labels))

    limiter = FPSLimiter(fps=max(1, int(args.fps)))
    monitor = OCRLatencyMonitor(mode=mode)
    monitor.annotate("synthetic", bool(args.synthetic))
    monitor.annotate("ocr_language", config.ocr_language)
    monitor.annotate("ocr_psm", config.ocr_psm)
    monitor.annotate("ground_max_labels", ground_max_labels)

    logger.info(
        "OCR bench starting | samples=%d fps=%d mode=%s synthetic=%s",
        samples,
        max(1, int(args.fps)),
        mode,
        args.synthetic,
    )

    for sample_idx in range(samples):
        total_start = time.monotonic()

        stage_start = time.monotonic()
        frame = frame_provider()
        capture_ms = (time.monotonic() - stage_start) * 1000.0

        teammate_ms = 0.0
        ground_ms = 0.0
        teammate_count = 0
        ground_count = 0

        if mode in {"teammate", "both"}:
            stage_start = time.monotonic()
            teammate_count = len(vision.find_teammates(frame, require_ocr=True))
            teammate_ms = (time.monotonic() - stage_start) * 1000.0

        if mode in {"ground", "both"}:
            stage_start = time.monotonic()
            ground_count = len(vision.scan_ground_item_labels(frame, max_labels=ground_max_labels))
            ground_ms = (time.monotonic() - stage_start) * 1000.0

        total_ms = (time.monotonic() - total_start) * 1000.0

        monitor.record(
            OCRBenchmarkSample(
                capture_ms=float(capture_ms),
                teammate_ocr_ms=float(teammate_ms),
                ground_ocr_ms=float(ground_ms),
                total_ms=float(total_ms),
                teammate_count=int(teammate_count),
                ground_count=int(ground_count),
            )
        )

        if config.debug and (sample_idx + 1) % max(1, min(samples, 20)) == 0:
            logger.debug(
                "OCR bench progress %d/%d | capture_ms=%.2f teammate_ms=%.2f ground_ms=%.2f total_ms=%.2f",
                sample_idx + 1,
                samples,
                capture_ms,
                teammate_ms,
                ground_ms,
                total_ms,
            )

        limiter.wait()

    summary = monitor.summarize()
    reporter = JSONOCRBenchmarkReporter(config.perf_report_dir)
    explicit_output = Path(args.output_json) if args.output_json else None
    report_path = reporter.write(summary, explicit_output)

    logger.info(
        "OCR BENCH RESULT | samples=%d mode=%s achieved_fps=%.2f avg_total_ms=%.2f p95_total_ms=%.2f p99_total_ms=%.2f",
        summary.samples,
        summary.mode,
        summary.achieved_fps,
        summary.avg_total_ms,
        summary.p95_total_ms,
        summary.p99_total_ms,
    )
    logger.info(
        "OCR BENCH COUNTS | avg_teammate=%.2f avg_ground=%.2f",
        summary.avg_teammate_count,
        summary.avg_ground_count,
    )
    logger.info("OCR benchmark report written to: %s", report_path)

    for stage, stats in summary.stage_stats.items():
        logger.info(
            "OCR STAGE %s | avg_ms=%.2f p95_ms=%.2f p99_ms=%.2f max_ms=%.2f",
            stage,
            stats.avg_ms,
            stats.p95_ms,
            stats.p99_ms,
            stats.max_ms,
        )

def run_perf_test(config: RuntimeConfig, args: argparse.Namespace, logger):
    # Perf runs default to dry-run for safety unless explicitly overridden.
    """Run perf test.

    Parameters:
        config: Parameter containing configuration values that guide behavior.
        args: Parameter for args used in this routine.
        logger: Parameter used to emit diagnostic log messages.

    Local Variables:
        explicit_output: Local variable for explicit output used in this routine.
        frame_limit: Local variable representing image frame data for vision processing.
        frame_provider: Local variable representing image frame data for vision processing.
        monitor: Local variable for monitor used in this routine.
        perf_config: Local variable containing configuration values that guide behavior.
        report_path: Local variable containing a filesystem location.
        reporter: Local variable for reporter used in this routine.
        samples: Local variable for samples used in this routine.
        stage: Local variable for stage used in this routine.
        stats: Local variable for stats used in this routine.
        summary: Local variable for summary used in this routine.
        target_fps: Local variable for target fps used in this routine.
        vision: Local variable for vision used in this routine.
        warmup: Local variable for warmup used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    perf_config = replace(config, dry_run=(not args.live_input))

    run_startup_checks(perf_config, logger)

    if args.synthetic:
        vision, frame_provider = prepare_synthetic_vision(perf_config, logger, args.synthetic_image)
    else:
        _, _, vision = prepare_window_and_vision(perf_config, logger)
        frame_provider = vision.grab_frame

    warmup = max(0, int(args.warmup_frames))
    samples = max(1, int(args.frames))
    target_fps = float(args.target_fps)
    frame_limit = warmup + samples

    monitor = PerformanceMonitor(target_fps=target_fps, warmup_frames=warmup)

    _run_frame_loop(
        config=perf_config,
        logger=logger,
        vision=vision,
        frame_provider=frame_provider,
        frame_limit=frame_limit,
        monitor=monitor,
    )

    summary = monitor.summarize()
    reporter = JSONPerfReporter(perf_config.perf_report_dir)
    explicit_output = Path(args.output_json) if args.output_json else None
    report_path = reporter.write(summary, explicit_output)

    logger.info(
        "PERF RESULT | sampled=%d warmup=%d target_fps=%.2f achieved_fps=%.2f avg_ms=%.2f p95_ms=%.2f pass=%s",
        summary.sampled_frames,
        summary.warmup_frames,
        summary.target_fps,
        summary.achieved_fps,
        summary.avg_frame_ms,
        summary.p95_frame_ms,
        summary.meets_target,
    )
    logger.info("Performance report written to: %s", report_path)

    if summary.annotations:
        logger.info("PERF ANNOTATIONS | %s", summary.annotations)

    for stage, stats in summary.stage_stats.items():
        logger.info(
            "STAGE %s | avg_ms=%.2f p95_ms=%.2f max_ms=%.2f",
            stage,
            stats.avg_ms,
            stats.p95_ms,
            stats.max_ms,
        )



def main():
    """Main.

    Parameters:
        None.

    Local Variables:
        args: Local variable for args used in this routine.
        config: Local variable containing configuration values that guide behavior.
        logger: Local variable used to emit diagnostic log messages.
        parser: Local variable for parser used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = make_config(args)
    except ValueError as exc:
        parser.error(str(exc))

    logger = configure_logging(config)

    try:
        if args.command == "run":
            run_loop(config, logger)
        elif args.command == "center-window":
            run_center_window(config, logger)
        elif args.command == "collect-ocr":
            run_collect_ocr(config, args, logger)
        elif args.command == "perf-test":
            run_perf_test(config, args, logger)
        elif args.command == "ocr-bench":
            run_ocr_bench(config, args, logger)
        else:
            parser.error(f"Unknown command: {args.command}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
































