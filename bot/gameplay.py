"""Timed gameplay scan + action routines for general Diablo II maintenance tasks."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Dict, List, Optional, Tuple

from bot.config import RuntimeConfig
from bot.controller import Action
from bot.game_state import BeltStatus, GameState, GroundItemDetection, PickitMatch, ResourceStatus


@dataclass(frozen=True)
class GameplayStats:
    resource_scans: int
    belt_scans: int
    ground_scans: int
    pickit_matches: int
    potion_actions: int
    pickup_actions: int
    buff_checks: int
    merc_checks: int
    inventory_checks: int


class _IntervalScheduler:
    def __init__(self):
        """Initialize a new `_IntervalScheduler` instance.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._last_run: Dict[str, float] = {}

    def due(self, name: str, interval_s: float, now: float) -> bool:
        """Due.

        Parameters:
            name: Parameter for name used in this routine.
            interval_s: Parameter storing a duration value in seconds.
            now: Parameter for now used in this routine.

        Local Variables:
            interval: Local variable for interval used in this routine.
            last: Local variable for last used in this routine.

        Returns:
            A value matching the annotated return type `bool`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        interval = max(0.0, float(interval_s))
        last = self._last_run.get(name)
        if last is None or (now - last) >= interval:
            self._last_run[name] = now
            return True
        return False


class GameplayScanner:
    """Runs heavier perception tasks at independent cadences and enriches GameState."""

    def __init__(self, config: RuntimeConfig, pickit_db):
        """Initialize a new `GameplayScanner` instance.

        Parameters:
            config: Parameter containing configuration values that guide behavior.
            pickit_db: Parameter for pickit db used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.config = config
        self.pickit_db = pickit_db
        self._scheduler = _IntervalScheduler()

        self._cached_resource: Optional[ResourceStatus] = None
        self._cached_belt: Optional[BeltStatus] = None
        self._cached_ground_items: List[GroundItemDetection] = []
        self._cached_gold_items: List[GroundItemDetection] = []
        self._cached_pickit_matches: List[PickitMatch] = []

        self._resource_scans = 0
        self._belt_scans = 0
        self._ground_scans = 0
        self._pickit_match_total = 0
        self._buff_checks = 0
        self._merc_checks = 0
        self._inventory_checks = 0

    def enrich_state(self, vision, frame, state: GameState, now_monotonic: Optional[float] = None) -> GameState:
        """Enrich state.

        Parameters:
            vision: Parameter for vision used in this routine.
            frame: Parameter representing image frame data for vision processing.
            state: Parameter carrying runtime state information.
            now_monotonic: Parameter for now monotonic used in this routine.

        Local Variables:
            d: Local variable for d used in this routine.
            detections: Local variable for detections used in this routine.
            now: Local variable for now used in this routine.

        Returns:
            A value matching the annotated return type `GameState`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        now = time.monotonic() if now_monotonic is None else float(now_monotonic)

        if not self.config.enable_gameplay_timers:
            return state

        if self._scheduler.due("resource_scan", self.config.resource_scan_interval_s, now):
            self._cached_resource = vision.scan_resource_status(frame)
            self._resource_scans += 1

        if self._scheduler.due("belt_scan", self.config.belt_scan_interval_s, now):
            self._cached_belt = vision.scan_belt_status(frame)
            self._belt_scans += 1

        if self._scheduler.due("ground_scan", self.config.ground_item_scan_interval_s, now):
            detections = vision.scan_ground_item_labels(
                frame,
                max_labels=self.config.ground_item_scan_max_labels,
            )
            self._cached_ground_items = list(detections)
            self._cached_gold_items = [d for d in detections if d.is_gold]
            self._ground_scans += 1

            if self.config.enable_pickit:
                self._cached_pickit_matches = self.pickit_db.pick_candidates(self._cached_ground_items)
            else:
                self._cached_pickit_matches = []

            self._pickit_match_total += len(self._cached_pickit_matches)

        if self._scheduler.due("buff_check", self.config.buff_check_interval_s, now):
            self._run_buff_maintenance_stub(state)

        if self._scheduler.due("merc_check", self.config.merc_check_interval_s, now):
            self._run_mercenary_check_stub(state)

        if self._scheduler.due("inventory_check", self.config.inventory_check_interval_s, now):
            self._run_inventory_check_stub(state)

        state.resource_status = self._cached_resource
        state.belt_status = self._cached_belt
        state.ground_items = list(self._cached_ground_items)
        state.gold_items = list(self._cached_gold_items)
        state.pickit_matches = list(self._cached_pickit_matches)
        return state

    def stats(self) -> GameplayStats:
        """Stats.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `GameplayStats`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return GameplayStats(
            resource_scans=self._resource_scans,
            belt_scans=self._belt_scans,
            ground_scans=self._ground_scans,
            pickit_matches=self._pickit_match_total,
            potion_actions=0,
            pickup_actions=0,
            buff_checks=self._buff_checks,
            merc_checks=self._merc_checks,
            inventory_checks=self._inventory_checks,
        )

    def _run_buff_maintenance_stub(self, state: GameState):
        # Hook for future class-specific buff upkeep (BO, CTA, armor, golem, etc.).
        """Internal helper to run buff maintenance stub.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        _ = state
        self._buff_checks += 1

    def _run_mercenary_check_stub(self, state: GameState):
        # Hook for future mercenary status checks and potion support.
        """Internal helper to run mercenary check stub.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        _ = state
        self._merc_checks += 1

    def _run_inventory_check_stub(self, state: GameState):
        # Hook for future stash/sell logic and inventory-pressure safeguards.
        """Internal helper to run inventory check stub.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        _ = state
        self._inventory_checks += 1

class GameplayActionPlanner:
    """Turns periodic gameplay signals into concrete actions with cooldown protection."""

    def __init__(self, config: RuntimeConfig):
        """Initialize a new `GameplayActionPlanner` instance.

        Parameters:
            config: Parameter containing configuration values that guide behavior.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.config = config
        self._scheduler = _IntervalScheduler()

        self._potion_actions = 0
        self._pickup_actions = 0

    def decide(
        self,
        state: GameState,
        now_monotonic: Optional[float] = None,
        allow_potions: Optional[bool] = None,
        allow_pickups: Optional[bool] = None,
    ) -> Optional[Action]:
        """Decide.

        Parameters:
            state: Parameter carrying runtime state information.
            now_monotonic: Parameter for now monotonic used in this routine.

        Local Variables:
            now: Local variable for now used in this routine.
            pickup_action: Local variable for pickup action used in this routine.
            potion_action: Local variable for potion action used in this routine.

        Returns:
            A value matching the annotated return type `Optional[Action]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        now = time.monotonic() if now_monotonic is None else float(now_monotonic)

        if not self.config.enable_gameplay_timers or state.loading:
            return None

        potion_action = self._decide_potion_action(state, now, allow_potions=allow_potions)
        if potion_action is not None:
            self._potion_actions += 1
            return potion_action

        if self._has_active_threats(state) and self.config.pickup_disable_when_enemies:
            return None

        pickup_action = self._decide_pickup_action(state, now, allow_pickups=allow_pickups)
        if pickup_action is not None:
            self._pickup_actions += 1
            return pickup_action

        return None

    def stats(self) -> GameplayStats:
        """Stats.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `GameplayStats`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return GameplayStats(
            resource_scans=0,
            belt_scans=0,
            ground_scans=0,
            pickit_matches=0,
            potion_actions=self._potion_actions,
            pickup_actions=self._pickup_actions,
            buff_checks=0,
            merc_checks=0,
            inventory_checks=0,
        )

    def _decide_potion_action(self, state: GameState, now: float, allow_potions: Optional[bool] = None) -> Optional[Action]:
        """Internal helper to decide potion action.

        Parameters:
            state: Parameter carrying runtime state information.
            now: Parameter for now used in this routine.

        Local Variables:
            resource: Local variable for resource used in this routine.

        Returns:
            A value matching the annotated return type `Optional[Action]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if allow_potions is False:
            return None

        if not self.config.enable_belt_management:
            return None

        resource = state.resource_status
        if resource is None:
            return None

        if (
            resource.health_ratio <= self.config.health_potion_trigger_ratio
            and self._scheduler.due("drink_health", self.config.potion_action_cooldown_s, now)
        ):
            return Action(
                cast_spell=self.config.health_potion_action_slot,
                reason=f"belt_manage_health_{resource.health_ratio:.2f}",
            )

        if (
            resource.mana_ratio <= self.config.mana_potion_trigger_ratio
            and self._scheduler.due("drink_mana", self.config.potion_action_cooldown_s, now)
        ):
            return Action(
                cast_spell=self.config.mana_potion_action_slot,
                reason=f"belt_manage_mana_{resource.mana_ratio:.2f}",
            )

        return None

    def _decide_pickup_action(self, state: GameState, now: float, allow_pickups: Optional[bool] = None) -> Optional[Action]:
        """Internal helper to decide pickup action.

        Parameters:
            state: Parameter carrying runtime state information.
            now: Parameter for now used in this routine.

        Local Variables:
            best_gold: Local variable for best gold used in this routine.
            target: Local variable for target used in this routine.

        Returns:
            A value matching the annotated return type `Optional[Action]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        if allow_pickups is False:
            return None

        if self.config.enable_pickit and self.config.enable_item_pickup and state.pickit_matches:
            if self._scheduler.due("pickup_action", self.config.pickup_click_cooldown_s, now):
                target = self._select_pickit_target(state.pickit_matches, state.player_position)
                if target is not None:
                    return Action(
                        click_target=target.item.position,
                        reason=f"pickit_pickup_{target.rule_name}",
                    )

        if self.config.enable_gold_pickup and state.gold_items:
            if self._scheduler.due("pickup_gold_action", self.config.pickup_click_cooldown_s, now):
                best_gold = self._select_gold_target(state.gold_items, state.player_position)
                if best_gold is not None and best_gold.gold_amount >= self.config.gold_pickup_min_amount:
                    return Action(
                        click_target=best_gold.position,
                        reason=f"pickup_gold_{best_gold.gold_amount}",
                    )

        return None

    def active_threat_snapshot(self, state: GameState) -> List[Dict[str, object]]:
        """Expose active enemy danger metadata for avoidance/targeting consumers."""
        return state.enemy_threat_snapshot()

    def _has_active_threats(self, state: GameState) -> bool:
        # Keep legacy behavior (any active enemy blocks pickup) while making
        # danger/tag metadata available through active_threat_snapshot().
        """Internal helper to has active threats.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `bool`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return bool(self.active_threat_snapshot(state))

    def _select_pickit_target(self, matches: List[PickitMatch], player_pos: Tuple[int, int]) -> Optional[PickitMatch]:
        """Internal helper to select pickit target.

        Parameters:
            matches: Parameter for matches used in this routine.
            player_pos: Parameter for player pos used in this routine.

        Local Variables:
            dist_sq: Local variable for dist sq used in this routine.
            px: Local variable for px used in this routine.
            py: Local variable for py used in this routine.
            x: Local variable for x used in this routine.
            y: Local variable for y used in this routine.

        Returns:
            A value matching the annotated return type `Optional[PickitMatch]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if not matches:
            return None

        def score(match: PickitMatch):
            """Score.

            Parameters:
                match: Parameter for match used in this routine.

            Local Variables:
                dist_sq: Local variable for dist sq used in this routine.
                px: Local variable for px used in this routine.
                py: Local variable for py used in this routine.
                x: Local variable for x used in this routine.
                y: Local variable for y used in this routine.

            Returns:
                A computed value produced by the routine.

            Side Effects:
                - No direct side effects beyond returning computed values.
            """
            px, py = player_pos
            x, y = match.item.position
            dist_sq = (x - px) * (x - px) + (y - py) * (y - py)
            return (-match.priority, dist_sq, -match.item.confidence)

        return min(matches, key=score)

    def _select_gold_target(self, detections: List[GroundItemDetection], player_pos: Tuple[int, int]) -> Optional[GroundItemDetection]:
        """Internal helper to select gold target.

        Parameters:
            detections: Parameter for detections used in this routine.
            player_pos: Parameter for player pos used in this routine.

        Local Variables:
            dist_sq: Local variable for dist sq used in this routine.
            px: Local variable for px used in this routine.
            py: Local variable for py used in this routine.
            x: Local variable for x used in this routine.
            y: Local variable for y used in this routine.

        Returns:
            A value matching the annotated return type `Optional[GroundItemDetection]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if not detections:
            return None

        def score(item: GroundItemDetection):
            """Score.

            Parameters:
                item: Parameter for item used in this routine.

            Local Variables:
                dist_sq: Local variable for dist sq used in this routine.
                px: Local variable for px used in this routine.
                py: Local variable for py used in this routine.
                x: Local variable for x used in this routine.
                y: Local variable for y used in this routine.

            Returns:
                A computed value produced by the routine.

            Side Effects:
                - No direct side effects beyond returning computed values.
            """
            px, py = player_pos
            x, y = item.position
            dist_sq = (x - px) * (x - px) + (y - py) * (y - py)
            return (-item.gold_amount, dist_sq, -item.confidence)

        return min(detections, key=score)

