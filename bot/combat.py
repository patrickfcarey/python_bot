"""Combat routine stubs for future expansion."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from bot.config import NecromancerConfig
from bot.controller import Action
from bot.game_state import EnemyTrack, GameState


@dataclass(frozen=True)
class CombatDecision:
    """Structured combat decision output consumed by the runtime loop."""

    action: Action
    mode: str
    target_track_id: Optional[int]
    reason: str
    target_danger_priority: int = 0
    target_danger_label: str = "non_combat"
    target_danger_tags: Tuple[str, ...] = ()
    target_combat_relevant: bool = True
    target_priority_score: int = 0
    target_human_consensus_score: int = 0
    target_human_consensus_band: str = "routine"
    target_threat_vector_primary: str = "general_pressure"
    target_threat_vector_secondary: str = "none"
    target_engagement_profile: str = "mixed"
    target_avoidance_priority: bool = False


class CombatRoutine:
    """Select combat targets and build movement/cast actions."""

    def __init__(
        self,
        engage_range_px: int = 260,
        close_range_px: int = 35,
        spell_slot: str = "primary",
        prefer_combat: bool = False,
        spell_rotation: Tuple[str, ...] = ("primary",),
        class_name: str = "generic",
        necromancer_config: Optional[NecromancerConfig] = None,
    ):
        """Initialize combat behavior thresholds and class spell settings.

        Parameters:
            engage_range_px: Maximum pixel distance allowed for engaging a target.
            close_range_px: Distance threshold for switching from approach to cast-in-place behavior.
            spell_slot: Default spell slot when no class-specific override is selected.
            prefer_combat: Enables aggressive combat mode labels for downstream logic.
            spell_rotation: Ordered spell slot sequence used by non-class-specific casting.
            class_name: Character class profile name used for class-specific spell selection.
            necromancer_config: Optional necromancer timing and slot configuration.

        Local Variables:
            normalized_spell_rotation: Rotation sequence after empty entries are removed.
            configured_slot: Iteration variable for each spell slot from the incoming rotation.

        Returns:
            None. The constructor stores runtime configuration on the instance.

        Side Effects:
            - Updates instance state through private `self._*` attributes.
        """
        self._engage_range_sq = engage_range_px * engage_range_px
        self._close_range_sq = close_range_px * close_range_px
        self._spell_slot = spell_slot
        self._prefer_combat = prefer_combat
        self._class_name = class_name
        self._necromancer_config = necromancer_config

        normalized_spell_rotation = tuple(configured_slot for configured_slot in spell_rotation if configured_slot)
        if not normalized_spell_rotation:
            normalized_spell_rotation = (spell_slot,)
        self._spell_rotation = normalized_spell_rotation
        self._spell_rotation_index = 0
        self._spell_tick = 0

    def scan_for_threats(self, state: GameState) -> List[EnemyTrack]:
        """Return currently active enemy tracks that are not considered lost.

        Parameters:
            state: Current frame game state containing tracked enemies.

        Local Variables:
            tracked_enemy: Candidate enemy track evaluated for activity.

        Returns:
            List of active `EnemyTrack` records where `lost_frames == 0`.

        Side Effects:
            - No direct side effects; returns filtered data.
        """
        # Threat metadata (danger/tags/consensus/pressure scores) is carried on
        # EnemyTrack and used by weighted target selection below.
        return [tracked_enemy for tracked_enemy in state.enemy_tracks if tracked_enemy.lost_frames == 0]

    def _distance_sq(self, origin_position: Tuple[int, int], destination_position: Tuple[int, int]) -> int:
        """Compute squared distance between two 2D points.

        Parameters:
            origin_position: Start position as `(x, y)`.
            destination_position: End position as `(x, y)`.

        Local Variables:
            delta_x: Horizontal difference in pixels.
            delta_y: Vertical difference in pixels.

        Returns:
            Squared Euclidean distance in pixels.

        Side Effects:
            - No direct side effects; pure arithmetic helper.
        """
        delta_x = destination_position[0] - origin_position[0]
        delta_y = destination_position[1] - origin_position[1]
        return (delta_x * delta_x) + (delta_y * delta_y)

    def _target_weighted_score(self, player_position: Tuple[int, int], target_track: EnemyTrack) -> int:
        """Compute weighted score used to rank target priority.

        Parameters:
            player_position: Player position as `(x, y)`.
            target_track: Enemy track candidate being scored.

        Local Variables:
            distance_penalty: Soft penalty that increases with distance from the player.
            distance_squared: Squared pixel distance between player and target.
            weighted_score: Accumulated score from priority, threat pressure, and penalties.

        Returns:
            Integer weighted score where higher values indicate better target priority.

        Side Effects:
            - No direct side effects; pure scoring calculation.
        """
        distance_squared = self._distance_sq(player_position, target_track.position)
        distance_penalty = int(distance_squared / 900)  # soft penalty per ~30 px

        weighted_score = int(target_track.target_priority_score)
        if weighted_score <= 0:
            weighted_score = int(target_track.danger_priority) * 12

        weighted_score += int(target_track.human_consensus_score * 0.4)
        weighted_score += int(target_track.burst_pressure_rating) * 5
        weighted_score += int(target_track.control_pressure_rating) * 4
        weighted_score += int(target_track.attrition_pressure_rating) * 3
        weighted_score += int(target_track.spawn_pressure_rating) * 2

        if target_track.avoidance_priority:
            weighted_score += 6
        if not target_track.combat_relevant:
            weighted_score -= 40

        return weighted_score - distance_penalty

    def select_target(
        self,
        player_position: Tuple[int, int],
        threat_tracks: List[EnemyTrack],
    ) -> Optional[EnemyTrack]:
        """Select the highest-ranked target among active threats.

        Parameters:
            player_position: Player position as `(x, y)` used for distance tie-breaking.
            threat_tracks: Active threat candidates to rank.

        Local Variables:
            ranked_targets: Threat list sorted by weighted score, distance, then track id.

        Returns:
            Best `EnemyTrack` candidate, or `None` when no threats are available.

        Side Effects:
            - No direct side effects; returns selected record from input list.
        """
        if not threat_tracks:
            return None

        ranked_targets = sorted(
            threat_tracks,
            key=lambda tracked_enemy: (
                -self._target_weighted_score(player_position, tracked_enemy),
                self._distance_sq(player_position, tracked_enemy.position),
                tracked_enemy.track_id,
            ),
        )
        return ranked_targets[0]

    def should_engage(self, player_position: Tuple[int, int], target_track: EnemyTrack) -> bool:
        """Return whether the target is close enough to engage.

        Parameters:
            player_position: Player position as `(x, y)`.
            target_track: Selected target track for engagement testing.

        Local Variables:
            delta_x: Horizontal distance to the target in pixels.
            delta_y: Vertical distance to the target in pixels.

        Returns:
            `True` when squared distance is within the configured engage radius.

        Side Effects:
            - No direct side effects; deterministic range check.
        """
        delta_x = target_track.position[0] - player_position[0]
        delta_y = target_track.position[1] - player_position[1]
        return (delta_x * delta_x) + (delta_y * delta_y) <= self._engage_range_sq

    def _next_rotation_spell(self) -> str:
        """Return next spell slot from the configured rotation sequence.

        Parameters:
            None.

        Local Variables:
            selected_slot: Spell slot selected at the current rotation index.

        Returns:
            Spell slot identifier string.

        Side Effects:
            - Increments `self._spell_rotation_index` to advance the rotation state.
        """
        selected_slot = self._spell_rotation[self._spell_rotation_index % len(self._spell_rotation)]
        self._spell_rotation_index += 1
        return selected_slot

    def _cast_necromancer_spells_stub(self, distance_squared: float) -> str:
        """Choose a necromancer spell slot using basic tick-based timing.

        Parameters:
            distance_squared: Squared distance to current target in pixels.

        Local Variables:
            current_spell_tick: Current tick index before incrementing cast cadence.
            necromancer_settings: Active necromancer config, if available.

        Returns:
            Selected spell slot string (`curse`, `summon`, or primary attack slot).

        Side Effects:
            - Increments `self._spell_tick` for cadence scheduling.
        """
        necromancer_settings = self._necromancer_config
        if necromancer_settings is None:
            return self._next_rotation_spell()

        current_spell_tick = self._spell_tick
        self._spell_tick += 1

        if current_spell_tick % max(1, int(necromancer_settings.curse_recast_frames)) == 0:
            return necromancer_settings.curse_spell_slot

        if (
            distance_squared <= self._close_range_sq
            and current_spell_tick % max(1, int(necromancer_settings.summon_recast_frames)) == 0
        ):
            return necromancer_settings.summon_spell_slot

        return necromancer_settings.primary_attack_slot

    def cast_spells_stub(self, state: GameState, target_track: EnemyTrack, distance_squared: float) -> str:
        """Select spell slot for the current class profile using stub logic.

        Parameters:
            state: Current game state (reserved for future class-specific logic expansion).
            target_track: Selected target track (reserved for future class-specific logic expansion).
            distance_squared: Squared distance to target.

        Local Variables:
            None declared in this function body.

        Returns:
            Spell slot string selected for this combat step.

        Side Effects:
            - Advances internal spell-rotation or spell-tick state.
        """
        if self._class_name == "necromancer" and self._necromancer_config is not None:
            return self._cast_necromancer_spells_stub(distance_squared)

        return self._next_rotation_spell()

    def build_combat_action(
        self,
        player_position: Tuple[int, int],
        target_track: EnemyTrack,
        spell_slot: str,
    ) -> Action:
        """Build the action used to approach or cast on a selected target.

        Parameters:
            player_position: Player position as `(x, y)`.
            target_track: Selected target enemy track.
            spell_slot: Spell slot chosen for this action tick.

        Local Variables:
            delta_x: Horizontal distance from player to target.
            delta_y: Vertical distance from player to target.
            distance_squared: Squared distance used to choose close-range behavior.

        Returns:
            `Action` configured for either cast-in-place or approach-and-cast behavior.

        Side Effects:
            - No direct side effects; action object is returned to caller.
        """
        delta_x = target_track.position[0] - player_position[0]
        delta_y = target_track.position[1] - player_position[1]
        distance_squared = (delta_x * delta_x) + (delta_y * delta_y)

        if distance_squared <= self._close_range_sq:
            return Action(
                hold_move=False,
                cast_spell=spell_slot,
                reason=f"combat_stub_cast_track_{target_track.track_id}",
            )

        return Action(
            click_target=target_track.position,
            cast_spell=spell_slot,
            reason=f"combat_stub_approach_track_{target_track.track_id}",
        )

    def decide(self, state: GameState) -> Optional[CombatDecision]:
        """Produce a combat decision from current game state and tracked enemies.

        Parameters:
            state: Current frame state with player position and enemy tracking metadata.

        Local Variables:
            action: Final action object for this decision tick.
            combat_mode: Decision mode label used by downstream logging and control flow.
            delta_x: Horizontal distance from player to selected target.
            delta_y: Vertical distance from player to selected target.
            distance_squared: Squared distance used for class spell and action decisions.
            selected_spell_slot: Spell slot selected for this tick.
            selected_target_track: Highest-ranked target track candidate.
            threat_tracks: Active threat tracks available for selection.

        Returns:
            `CombatDecision` when a target is valid and engageable; otherwise `None`.

        Side Effects:
            - Advances internal spell rotation/tick state through spell selection helpers.
        """
        threat_tracks = self.scan_for_threats(state)
        selected_target_track = self.select_target(state.player_position, threat_tracks)
        if selected_target_track is None:
            return None

        if not self.should_engage(state.player_position, selected_target_track):
            return None

        delta_x = selected_target_track.position[0] - state.player_position[0]
        delta_y = selected_target_track.position[1] - state.player_position[1]
        distance_squared = (delta_x * delta_x) + (delta_y * delta_y)

        selected_spell_slot = self.cast_spells_stub(state, selected_target_track, distance_squared)
        action = self.build_combat_action(state.player_position, selected_target_track, selected_spell_slot)
        combat_mode = "combat_stub_aggressive" if self._prefer_combat else "combat_stub_active"

        if self._class_name == "necromancer":
            combat_mode = "combat_stub_necromancer"

        return CombatDecision(
            action=action,
            mode=combat_mode,
            target_track_id=selected_target_track.track_id,
            reason=action.reason,
            target_danger_priority=int(selected_target_track.danger_priority),
            target_danger_label=str(selected_target_track.danger_label),
            target_danger_tags=tuple(selected_target_track.danger_tags),
            target_combat_relevant=bool(selected_target_track.combat_relevant),
            target_priority_score=int(selected_target_track.target_priority_score),
            target_human_consensus_score=int(selected_target_track.human_consensus_score),
            target_human_consensus_band=str(selected_target_track.human_consensus_band),
            target_threat_vector_primary=str(selected_target_track.threat_vector_primary),
            target_threat_vector_secondary=str(selected_target_track.threat_vector_secondary),
            target_engagement_profile=str(selected_target_track.engagement_profile),
            target_avoidance_priority=bool(selected_target_track.avoidance_priority),
        )
