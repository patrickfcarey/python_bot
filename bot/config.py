"""Runtime configuration and defaults for the bot."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

DEFAULT_FOLLOW_RADIUS = 14


@dataclass(frozen=True)
class NecromancerConfig:
    follow_radius: int = 16
    curse_spell_slot: str = "curse"
    primary_attack_slot: str = "primary"
    summon_spell_slot: str = "summon"
    curse_recast_frames: int = 36
    summon_recast_frames: int = 140


@dataclass(frozen=True)
class CharacterProfile:
    name: str
    description: str = ""
    class_name: str = "generic"
    turn_sensitivity: float = 0.24
    follow_radius: int = DEFAULT_FOLLOW_RADIUS
    prefer_combat: bool = False
    combat_engage_range_px: int = 260
    combat_close_range_px: int = 35
    combat_spell_slot: str = "primary"
    combat_spell_rotation: Tuple[str, ...] = ("primary",)
    spell_keys: Dict[str, str] = field(default_factory=dict)
    necromancer: Optional[NecromancerConfig] = None



def default_character_profiles() -> Dict[str, CharacterProfile]:
    """Default character profiles.

    Parameters:
        None.

    Local Variables:
        necromancer_behavior: Local variable for necromancer behavior used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, CharacterProfile]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    necromancer_behavior = NecromancerConfig(
        follow_radius=18,
        curse_spell_slot="curse",
        primary_attack_slot="primary",
        summon_spell_slot="summon",
        curse_recast_frames=32,
        summon_recast_frames=120,
    )

    return {
        "balanced": CharacterProfile(
            name="balanced",
            description="General follower profile with stable movement and low combat priority.",
            class_name="generic",
            turn_sensitivity=0.24,
            follow_radius=14,
            prefer_combat=False,
            combat_engage_range_px=260,
            combat_close_range_px=35,
            combat_spell_slot="primary",
            combat_spell_rotation=("primary",),
            spell_keys={"primary": "1"},
        ),
        "sorc_tele": CharacterProfile(
            name="sorc_tele",
            description="Faster repositioning and wider follow radius for teleport-heavy movement.",
            class_name="sorceress",
            turn_sensitivity=0.34,
            follow_radius=20,
            prefer_combat=False,
            combat_engage_range_px=235,
            combat_close_range_px=28,
            combat_spell_slot="primary",
            combat_spell_rotation=("primary", "primary", "mobility"),
            spell_keys={"primary": "1", "mobility": "2"},
        ),
        "hammerdin": CharacterProfile(
            name="hammerdin",
            description="Tighter follow spacing and stronger combat preference.",
            class_name="paladin",
            turn_sensitivity=0.20,
            follow_radius=10,
            prefer_combat=True,
            combat_engage_range_px=300,
            combat_close_range_px=48,
            combat_spell_slot="primary",
            combat_spell_rotation=("primary", "primary"),
            spell_keys={"primary": "2"},
        ),
        "frenzy_barb": CharacterProfile(
            name="frenzy_barb",
            description="Close-range aggressive profile with tight chase behavior.",
            class_name="barbarian",
            turn_sensitivity=0.18,
            follow_radius=8,
            prefer_combat=True,
            combat_engage_range_px=280,
            combat_close_range_px=24,
            combat_spell_slot="primary",
            combat_spell_rotation=("primary",),
            spell_keys={"primary": "1"},
        ),
        "necromancer": CharacterProfile(
            name="necromancer",
            description="Necromancer summoner/caster preset with curse and summon spell stubs.",
            class_name="necromancer",
            turn_sensitivity=0.22,
            follow_radius=necromancer_behavior.follow_radius,
            prefer_combat=True,
            combat_engage_range_px=300,
            combat_close_range_px=42,
            combat_spell_slot=necromancer_behavior.primary_attack_slot,
            combat_spell_rotation=(
                necromancer_behavior.curse_spell_slot,
                necromancer_behavior.primary_attack_slot,
                necromancer_behavior.primary_attack_slot,
                necromancer_behavior.summon_spell_slot,
            ),
            spell_keys={
                "primary": "1",
                "curse": "2",
                "summon": "3",
            },
            necromancer=necromancer_behavior,
        ),
    }


@dataclass(frozen=True)
class RuntimeConfig:
    fps: int = 20
    loading_brightness_threshold: float = 32.0
    loading_stddev_threshold: float = 18.0
    level_stabilize_time: float = 2.0
    turn_sensitivity: float = 0.24
    follow_radius: int = DEFAULT_FOLLOW_RADIUS
    # Backward-compatible alias for old config/tests.
    follow_deadzone_px: int = DEFAULT_FOLLOW_RADIUS
    teammate_min_separation_px: int = 12
    teammate_template_threshold: float = 0.80

    move_key: str = "w"
    stop_key: str = "s"
    spell_keys: Dict[str, str] = field(
        default_factory=lambda: {
            "primary": "1",
            "belt_health": "1",
            "belt_mana": "2",
            "belt_rejuv": "3",
        }
    )

    # Window targeting and placement.
    auto_center_window: bool = True
    game_window_keywords: Tuple[str, ...] = (
        "diablo ii",
        "diablo ii: resurrected",
        "diablo",
    )
    ocr_window_keywords: Tuple[str, ...] = (
        "diablo",
        "resurrected",
    )
    min_window_width: int = 800
    min_window_height: int = 600

    # Automap crop settings, relative to game window top-left.
    automap_offset_x: int = 0
    automap_offset_y: int = 0
    automap_width: int = 800
    automap_height: int = 600

    # OCR and detection.
    ocr_language: str = "eng"
    ocr_psm: int = 7
    ocr_name_confidence_threshold: float = 40.0

    # OCR chat command controls.
    chat_commands_enabled: bool = True
    chat_command_prefix: str = "!"
    chat_command_allow_no_prefix: bool = False
    chat_command_require_sender: bool = False
    chat_command_allowed_senders: Tuple[str, ...] = tuple()
    chat_command_poll_interval_s: float = 0.35
    chat_command_dedupe_window_s: float = 1.20
    chat_command_max_lines: int = 6
    chat_command_max_actions_per_poll: int = 4
    chat_command_ocr_confidence_threshold: float = 40.0
    chat_command_roi_left_pct: float = 0.01
    chat_command_roi_top_pct: float = 0.60
    chat_command_roi_right_pct: float = 0.55
    chat_command_roi_bottom_pct: float = 0.98

    # Manual keyboard pause/resume hotkey controls.
    pause_hotkey_enabled: bool = True
    pause_hotkey_debounce_s: float = 0.30

    # Enemy and combat stubs.
    enable_combat_stub: bool = False
    enemy_scan_min_area: int = 16
    enemy_scan_max_area: int = 450
    enemy_track_match_distance_px: float = 40.0
    enemy_track_max_lost_frames: int = 6
    combat_engage_range_px: int = 260
    combat_close_range_px: int = 35

    # Timed gameplay maintenance routines.
    enable_gameplay_timers: bool = True
    enable_belt_management: bool = True
    enable_pickit: bool = True
    enable_item_pickup: bool = True
    enable_gold_pickup: bool = True
    pickup_disable_when_enemies: bool = True

    resource_scan_interval_s: float = 0.10
    belt_scan_interval_s: float = 0.40
    ground_item_scan_interval_s: float = 0.55
    buff_check_interval_s: float = 1.50
    merc_check_interval_s: float = 2.50
    inventory_check_interval_s: float = 3.00

    health_potion_trigger_ratio: float = 0.45
    mana_potion_trigger_ratio: float = 0.35
    potion_action_cooldown_s: float = 0.75
    pickup_click_cooldown_s: float = 0.35
    gold_pickup_min_amount: int = 400

    health_potion_action_slot: str = "belt_health"
    mana_potion_action_slot: str = "belt_mana"
    rejuvenation_potion_action_slot: str = "belt_rejuv"

    belt_rows: int = 4
    belt_columns: int = 4
    ground_item_scan_max_labels: int = 12
    ground_item_ocr_confidence_threshold: float = 35.0

    # Character behavior profile.
    active_profile: str = "legacy"
    character_profiles: Dict[str, CharacterProfile] = field(default_factory=default_character_profiles)

    # Performance testing defaults.
    perf_target_fps: float = 50.0
    perf_warmup_frames: int = 120
    perf_sample_frames: int = 600
    perf_report_dir: Path = Path("logs/perf")
    # Async vision pipeline settings.
    vision_async_enabled: bool = True
    vision_async_max_result_age_ms: float = 160.0
    vision_async_workers: int = 2
    vision_async_max_pending_jobs: int = 4

    # Observer and learning data capture.
    observer_enabled: bool = True
    observer_drop_policy: str = "drop_oldest"
    observer_event_queue_size: int = 4096
    observer_event_batch_size: int = 128
    observer_flush_interval_ms: int = 200
    observer_schema_version: int = 1
    observer_output_dir: Path = Path("logs/observer")

    observer_capture_full_frames: bool = True
    observer_full_frame_sample_fps: float = 1.0
    observer_high_threat_frame_capture: bool = True
    observer_high_threat_min_danger: int = 4
    observer_high_threat_cooldown_s: float = 1.0
    observer_image_queue_size: int = 96
    observer_image_jpeg_quality: int = 82
    observer_image_output_dir: Path = Path("logs/observer/frame_samples")

    observer_coverage_target_samples: int = 300
    observer_shadow_enabled: bool = True
    observer_shadow_include_loading: bool = False
    observer_shadow_min_confidence: float = 0.55

    # File system paths.
    teammate_template_path: Path = Path("bot/templates/green_x.png")
    screenshot_path: Path = Path("bot/tests/screenshots")
    ocr_dataset_raw_dir: Path = Path("data/ocr/raw")
    ocr_dataset_labeled_dir: Path = Path("data/ocr/labeled")
    pickit_db_path: Path = Path("data/pickit/default_pickit.json")
    log_dir: Path = Path("logs")

    # Runtime controls.
    debug: bool = False
    dry_run: bool = False
    max_frames: int = 0

    def available_profiles(self) -> Tuple[str, ...]:
        """Available profiles.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Tuple[str, ...]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return ("legacy",) + tuple(sorted(self.character_profiles.keys()))

    def _resolve_legacy_follow_radius(self) -> int:
        """Internal helper to resolve legacy follow radius.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if self.follow_radius != DEFAULT_FOLLOW_RADIUS:
            return self.follow_radius
        if self.follow_deadzone_px != DEFAULT_FOLLOW_RADIUS:
            return self.follow_deadzone_px
        return DEFAULT_FOLLOW_RADIUS

    def _legacy_profile(self) -> CharacterProfile:
        """Internal helper to legacy profile.

        Parameters:
            None.

        Local Variables:
            resolved_follow_radius: Local variable for resolved follow radius used in this routine.

        Returns:
            A value matching the annotated return type `CharacterProfile`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        resolved_follow_radius = self._resolve_legacy_follow_radius()
        return CharacterProfile(
            name="legacy",
            description="Use top-level RuntimeConfig movement/combat values.",
            class_name="generic",
            turn_sensitivity=self.turn_sensitivity,
            follow_radius=resolved_follow_radius,
            prefer_combat=False,
            combat_engage_range_px=self.combat_engage_range_px,
            combat_close_range_px=self.combat_close_range_px,
            combat_spell_slot="primary",
            combat_spell_rotation=("primary",),
            spell_keys=dict(self.spell_keys),
            necromancer=None,
        )

    def get_active_profile(self) -> CharacterProfile:
        """Get active profile.

        Parameters:
            None.

        Local Variables:
            merged_spell_keys: Local variable for merged spell keys used in this routine.
            profile: Local variable for profile used in this routine.
            resolved_follow_radius: Local variable for resolved follow radius used in this routine.

        Returns:
            A value matching the annotated return type `CharacterProfile`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        if self.active_profile == "legacy":
            return self._legacy_profile()

        profile = self.character_profiles.get(self.active_profile)
        if profile is None:
            return self._legacy_profile()

        merged_spell_keys = dict(self.spell_keys)
        merged_spell_keys.update(profile.spell_keys)

        resolved_follow_radius = profile.follow_radius
        if profile.class_name == "necromancer" and profile.necromancer is not None:
            resolved_follow_radius = max(1, int(profile.necromancer.follow_radius))

        return CharacterProfile(
            name=profile.name,
            description=profile.description,
            class_name=profile.class_name,
            turn_sensitivity=profile.turn_sensitivity,
            follow_radius=resolved_follow_radius,
            prefer_combat=profile.prefer_combat,
            combat_engage_range_px=profile.combat_engage_range_px,
            combat_close_range_px=profile.combat_close_range_px,
            combat_spell_slot=profile.combat_spell_slot,
            combat_spell_rotation=profile.combat_spell_rotation,
            spell_keys=merged_spell_keys,
            necromancer=profile.necromancer,
        )

    @property
    def effective_turn_sensitivity(self) -> float:
        """Effective turn sensitivity.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `float`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().turn_sensitivity

    @property
    def effective_follow_radius_px(self) -> int:
        """Effective follow radius px.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().follow_radius

    @property
    def effective_follow_deadzone_px(self) -> int:
        # Backward-compatible alias for existing call-sites.
        """Effective follow deadzone px.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return self.effective_follow_radius_px

    @property
    def effective_prefer_combat(self) -> bool:
        """Effective prefer combat.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `bool`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().prefer_combat

    @property
    def effective_combat_engage_range_px(self) -> int:
        """Effective combat engage range px.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().combat_engage_range_px

    @property
    def effective_combat_close_range_px(self) -> int:
        """Effective combat close range px.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().combat_close_range_px

    @property
    def effective_combat_spell_slot(self) -> str:
        """Effective combat spell slot.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `str`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().combat_spell_slot

    @property
    def effective_combat_spell_rotation(self) -> Tuple[str, ...]:
        """Effective combat spell rotation.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Tuple[str, ...]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().combat_spell_rotation

    @property
    def effective_spell_keys(self) -> Dict[str, str]:
        """Effective spell keys.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Dict[str, str]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().spell_keys

    @property
    def effective_class_name(self) -> str:
        """Effective class name.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `str`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().class_name

    @property
    def effective_necromancer_config(self) -> Optional[NecromancerConfig]:
        """Effective necromancer config.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Optional[NecromancerConfig]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self.get_active_profile().necromancer



def default_config() -> RuntimeConfig:
    """Default config.

    Parameters:
        None.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `RuntimeConfig`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return RuntimeConfig()



def profile_names() -> Tuple[str, ...]:
    """Profile names.

    Parameters:
        None.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `Tuple[str, ...]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return default_config().available_profiles()


