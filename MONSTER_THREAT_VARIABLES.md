# Monster Threat Variables (Final Pass)

This file defines the additional threat variables emitted by:

- `scripts/build_monster_family_groups.py`
- `data/web_seed_pack/processed/monsters/monster_family_groups.csv`
- `data/web_seed_pack/processed/monsters/monster_combat_profiles.csv`

## Variables

- `threat_vector_primary`: dominant threat shape.
- `threat_vector_secondary`: second-most relevant threat shape.
- `engagement_profile`: practical combat behavior profile.
- `mobility_class`: movement style (`stationary`, `slow_heavy`, `standard`, `kiting`, `fast`).
- `burst_pressure_rating`: burst lethality pressure (`0-5`).
- `control_pressure_rating`: debuff/crowd-control pressure (`0-5`).
- `attrition_pressure_rating`: drain/chip pressure (`0-5`).
- `spawn_pressure_rating`: summoner/resurrector pressure (`0-5`).
- `threat_rollup_rating`: combined threat pressure (`0-5`).
- `threat_intensity_rating`: danger+threat intensity rollup (`0-6`).
- `human_consensus_score`: board/reddit-mechanics weighted risk prior (`0-100`).
- `human_consensus_band`: `routine|caution|dangerous|feared|run_ending`.
- `consensus_source_bucket`: `mechanics_inferred|community_dangerous|community_feared|community_run_ending`.
- `target_priority_score`: deterministic targeting scalar (`0-100`).
- `avoidance_priority`: bool flag for targets that should bias avoidance behavior.
- `needs_line_of_sight_break`: bool hint for projectile/lightning pressure.
- `needs_corpse_control`: bool hint for on-death + resurrector ecosystems.
- `needs_debuff_response`: bool hint for curse/debuff-heavy enemies.

## How To Use

Targeting:
- Sort by `target_priority_score` descending.
- Apply distance as a soft penalty, not a hard override.

Avoidance:
- If `avoidance_priority=True`, increase stutter-step and spacing logic.
- If `needs_line_of_sight_break=True`, prefer pillar/wall pathing where possible.
- If `needs_corpse_control=True`, reserve corpse denial logic.

Party safety:
- Use `human_consensus_band` to escalate caution modes in hardcore-style profiles.

## Runtime Model Integration

`bot/game_state.py` (`EnemyDetection`/`EnemyTrack`) and `bot/combat.py` now expose these fields, so any planner can consume them without extra adapters.