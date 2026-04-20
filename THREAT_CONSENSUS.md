# Threat Consensus (Critical / Super-Critical / Human Opinion Layer)

Last updated: April 15, 2026.

## Scope

This file defines how `scripts/build_monster_family_groups.py` maps monsters into:

- `critical` / `super_critical` danger tiers
- human-opinion priors (`human_consensus_score`, `human_consensus_band`)

for the web-seed data pass.

## Human Consensus Summary

Across Reddit and long-running Diablo II forums, players repeatedly call out these threats:

- Run-ending tier: Dolls (`Stygian Doll`, `Soul Killer`) and soul-lightning mobs (`Burning Soul`, `Black Soul`, `Gloam`).
- Feared tier: Viper cloud family (`Tomb Viper`, `Serpent Magus`), frenzytaur family (`Death Lord`, `Moon Lord`, `Minion of Destruction`), and `Oblivion Knight` packs.
- Dangerous tier: Ranged pressure packs (archers/spear-cats/quill variants), curse-capable casters, and drain-heavy spirits.

## Rule Mapping In Code

`super_critical` remains intentionally narrow:

- canonical dolls: `Stygian Doll`, `Undead Stygian Doll`, `Soul Killer`, `Undead Soul Killer`
- canonical souls: `Burning Soul`, `Black Soul`, `Gloam`

`critical` includes:

- explicit viper/frenzytaur/oblivion-knight keywords
- act bosses
- constrained elite combinations (for example elite + heavy melee, elite + curse+ranged, elite + lightning burst)

Human-opinion layer:

- `human_consensus_score` blends danger tier + mechanics tags + consensus keyword buckets.
- `human_consensus_band` maps score into `routine|caution|dangerous|feared|run_ending`.
- `consensus_source_bucket` indicates whether the score was mostly from community priors or mechanics inference.

## Why This Split

- `danger_priority` drives deterministic combat risk.
- `human_consensus_score` captures player pain/risk perception that raw mechanics do not always expose.
- Together they give better target/avoidance tuning than either alone.

## Source Links Used

Official context:
- Blizzard D2R patch notes (viper cloud bug/fix context):
  - https://us.forums.blizzard.com/en/d2r/t/122-pc-patch-notes-23-build-67314/74018
- Blizzard forum danger discussions:
  - https://us.forums.blizzard.com/en/d2r/t/what-monster-do-you-fear-the-most/72239

Community consensus:
- Reddit: "Most dangerous enemy in D2 and D2R"
  - https://www.reddit.com/r/diablo2/comments/t4si6g/most_dangerous_enemy_in_d2_and_d2r_for_you_and_why/
- Reddit: "Dolls and Souls and maybe cursed/fanatacism"
  - https://www.reddit.com/r/diablo2/comments/qt2f6e/dolls_and_souls_and_maybe_cursedfanatacism/
- Reddit: "Frenzytaur question"
  - https://www.reddit.com/r/diablo2/comments/znf8f4/frenzytaur_question/
- Reddit: "Best enemy type to avoid in Hardcore"
  - https://www.reddit.com/r/diablo2/comments/1htyv3h/best_enemy_type_to_avoid_in_hardcore/

Long-tail forum context:
- https://www.diabloii.net/forums/threads/what-are-some-dangerous-monsters-according-to-you.964656/

## Caveats

- This is deterministic heuristic labeling from available seed fields (`display_name`, `mon_type`, `ai`, etc.).
- It does not yet ingest live aura/affix OCR states (Fanaticism, Conviction, Extra Strong, etc.).
- Treat these outputs as strong priors; final behavior should still combine live distance, confidence, and current combat context.