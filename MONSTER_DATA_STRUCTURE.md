# Monster Dataset Structure

This guide defines the structure you should fill for enemy recognition using:
- top-screen hover name OCR
- image-based monster matching ("monster symposium")

All paths are relative to repo root: `C:\github\python_bot`.

## 1) Directory Structure

```
data/monsters/
  raw/
    arreat_summit/
    in_game/
      hover_name_bar/
      body_crops/
      full_frames/
  processed/
    templates/
    features/
  labels/
    monster_catalog.template.jsonl
    frame_annotations.template.jsonl
    hover_name_ocr_labels.template.tsv
    monster_aliases.template.csv
    monster_index.template.csv
  splits/
    train.txt
    val.txt
    test.txt
  reports/
```

## 2) Filename Schemes (Use Exactly)

### 2.1 Arreat Summit sourced images
Path: `data/monsters/raw/arreat_summit/`

Scheme:
`arreat__<monster_slug>__variant<###>__idx<####>.png`

Examples:
- `arreat__fallen_shaman__variant001__idx0001.png`
- `arreat__venom_lord__variant003__idx0007.png`

### 2.2 In-game hover name bar crops (top of screen text)
Path: `data/monsters/raw/in_game/hover_name_bar/`

Scheme:
`hover__<monster_slug>__act<1-5>__zone<zone_slug>__diff<normal|nightmare|hell>__state<static|motion>__idx<####>.png`

Examples:
- `hover__fallen_shaman__act1__zoneblood_moor__diffnormal__statemotion__idx0012.png`
- `hover__venom_lord__act4__zonechaos_sanctuary__diffhell__statestatic__idx0004.png`

### 2.3 In-game monster body crops
Path: `data/monsters/raw/in_game/body_crops/`

Scheme:
`body__<monster_slug>__act<1-5>__zone<zone_slug>__view<front|side|rear>__dist<near|mid|far>__light<bright|dark|fx>__idx<####>.png`

Examples:
- `body__fallen_shaman__act1__zonecold_plains__viewside__distmid__lightdark__idx0033.png`
- `body__venom_lord__act4__zoneriver_of_flame__viewfront__distnear__lightfx__idx0015.png`

### 2.4 In-game full frames (optional but recommended)
Path: `data/monsters/raw/in_game/full_frames/`

Scheme:
`frame__<monster_slug>__act<1-5>__zone<zone_slug>__scenario<solo|pack|boss>__idx<####>.png`

## 3) Required Metadata Files

### 3.1 Monster catalog
File: `data/monsters/labels/monster_catalog.template.jsonl`

One JSON per line. Required fields:
- `monster_id` (stable ID, e.g., `m_fallen_shaman`)
- `slug` (filename-safe key)
- `display_name` (in-game display text)
- `family` (archetype group)
- `acts` (list)
- `areas` (list)
- `is_boss` (bool)
- `is_minion` (bool)
- `source_refs` (list of URLs or notes)

### 3.2 Frame annotations
File: `data/monsters/labels/frame_annotations.template.jsonl`

One JSON per line. Required fields:
- `image_path`
- `monster_id`
- `bbox` (`x`, `y`, `w`, `h`)
- `label_type` (`hover_text` or `body_visual`)
- `quality` (`high`, `medium`, `low`)
- `occlusion` (0.0-1.0)

### 3.3 Hover OCR labels
File: `data/monsters/labels/hover_name_ocr_labels.template.tsv`

Format:
`relative_path<TAB>monster_display_text`

Example:
`data/monsters/raw/in_game/hover_name_bar/hover__fallen_shaman__act1__zoneblood_moor__diffnormal__statemotion__idx0012.png	Fallen Shaman`

### 3.4 Monster aliases
File: `data/monsters/labels/monster_aliases.template.csv`

Columns:
`monster_id,alias`

Use for OCR normalization if hover text varies.

### 3.5 Monster index planner
File: `data/monsters/labels/monster_index.template.csv`

Columns:
`monster_id,slug,display_name,target_hover_images,target_body_images,covered`

Use this as your checklist to ensure full game coverage.

## 3.6) Required vs Optional Field Matrix (Tagging Contract)

Use this matrix as the consistency contract when filling templates manually.

| File | Field | Required | Type / Allowed Values | Default if Missing |
|---|---|---|---|---|
| `monster_catalog.template.jsonl` | `monster_id` | Yes | string, stable unique ID (`m_<slug>`) | none (must provide) |
| `monster_catalog.template.jsonl` | `slug` | Yes | filename-safe string | none (must provide) |
| `monster_catalog.template.jsonl` | `display_name` | Yes | in-game text string | none (must provide) |
| `monster_catalog.template.jsonl` | `family` | Yes | string family bucket | `unknown_untyped` |
| `monster_catalog.template.jsonl` | `acts` | Yes | list of ints (`1-5`) | empty list (invalid until filled) |
| `monster_catalog.template.jsonl` | `areas` | Yes | list of strings | empty list (invalid until filled) |
| `monster_catalog.template.jsonl` | `is_boss` | Yes | bool | `false` |
| `monster_catalog.template.jsonl` | `is_minion` | Yes | bool | `false` |
| `monster_catalog.template.jsonl` | `source_refs` | No | list of URLs/notes | `[]` |
| `monster_catalog.template.jsonl` | `combat_relevant` | Yes | bool | `false` |
| `monster_catalog.template.jsonl` | `danger_priority` | Yes | int `0-6` | `0` |
| `monster_catalog.template.jsonl` | `danger_label` | Yes | `non_combat|minimal|low|medium|high|critical|super_critical` | map from `danger_priority` |
| `monster_catalog.template.jsonl` | `combat_tags` | No | `|`-separated tag string or list | empty |
| `monster_catalog.template.jsonl` | `threat_vector_primary` | No | string | empty |
| `monster_catalog.template.jsonl` | `target_priority_score` | No | int `0-100` | `0` |
| `frame_annotations.template.jsonl` | `image_path` | Yes | relative path string | none (must provide) |
| `frame_annotations.template.jsonl` | `monster_id` | Yes | string, must exist in catalog | none (must provide) |
| `frame_annotations.template.jsonl` | `bbox` | Yes | object with positive ints `x,y,w,h` | none (must provide) |
| `frame_annotations.template.jsonl` | `label_type` | Yes | `hover_text|body_visual` | none (must provide) |
| `frame_annotations.template.jsonl` | `quality` | Yes | `high|medium|low` | `medium` |
| `frame_annotations.template.jsonl` | `occlusion` | Yes | float `0.0-1.0` | `0.0` |
| `hover_name_ocr_labels.template.tsv` | `relative_path` | Yes | relative image path | none (must provide) |
| `hover_name_ocr_labels.template.tsv` | `monster_display_text` | Yes | exact hover text label | none (must provide) |

Consistency rules:
- `danger_label` must always match `danger_priority` using the fixed scale in section 10.
- If `combat_relevant=false`, force `danger_priority=0` and `danger_label=non_combat`.
- Keep `monster_id` stable forever; do not rename once referenced by annotations.
- Treat optional fields as optional in ingestion, but fill them whenever known for better downstream tuning.

## 4) Minimum Collection Targets Per Monster

For each monster in `monster_index`:
- hover name OCR crops: minimum `25`
- body crops: minimum `40`

Suggested split per monster:
- Hover: `10 static + 15 motion`
- Body: `15 near + 15 mid + 10 far`

For bosses/superuniques, double targets:
- hover: `50`
- body: `80`

## 5) Processed Outputs You Will Generate Later

Path: `data/monsters/processed/templates/`

Suggested generated files:
- `<monster_slug>__template_primary.png`
- `<monster_slug>__template_alt_##.png`

Path: `data/monsters/processed/features/`

Suggested generated files:
- `<monster_slug>__embedding.npy`
- `<monster_slug>__descriptor.json`

## 6) Split Files

Files:
- `data/monsters/splits/train.txt`
- `data/monsters/splits/val.txt`
- `data/monsters/splits/test.txt`

Each line is a relative image path.

Recommended split:
- train 70%
- val 15%
- test 15%

## 7) Quick Start Checklist

1. Fill `monster_index.template.csv` with your target monsters.
2. Place raw images using filename schemes above.
3. Fill `monster_catalog.template.jsonl`.
4. Fill `hover_name_ocr_labels.template.tsv`.
5. Fill `frame_annotations.template.jsonl`.
6. Mark `covered=true` in index when minimum targets are met.


## 8) Dataset Coverage Validation

Use the validation script after you update `monster_index.template.csv`:

```powershell
python scripts/validate_monster_dataset.py --fail-on-missing
```

Optional report output:

```powershell
python scripts/validate_monster_dataset.py --output-json data/monsters/reports/coverage_report.json
```

## 9) Web Seed Family Grouping (For Classifier Planning)

If you are using the seeded d2data monster universe, generate normalized family groups with:

```powershell
python scripts/build_monster_family_groups.py
```

Outputs (under `data/web_seed_pack/processed/monsters/`):
- `monster_family_groups.csv` (every monstats row with assigned family group + broad archetype)
- `monster_family_groups_by_family.csv` (compact grouped summary)
- `monster_family_summary.json` (counts, examples, and any untyped rows)

Grouping logic:
- primary source is raw `mon_type` from `d2data_monstats.web_seed.csv`
- rows with blank `mon_type` are assigned with deterministic heuristics from `monstats_id`, `display_name`, and `ai`
- keeps an explicit `unknown_untyped` bucket for anything not confidently classifiable

This gives you stable family buckets for downstream OCR/image model planning while still being easy to replace when you move to your own sourced dataset.

## 10) Combat Relevance, Danger Priority, and Multi-Tag Traits

The web-seed grouping builder emits a finalized combat classification layer for each monster row.

Rebuild command:

```powershell
python scripts/build_monster_family_groups.py
```

Additional output:
- `data/web_seed_pack/processed/monsters/monster_combat_profiles.csv`

Extended columns now included in `monster_family_groups.csv` and `monster_combat_profiles.csv`:
- `combat_relevant` (`True`/`False`)
- `danger_priority` (`0-6`)
- `danger_label` (`non_combat|minimal|low|medium|high|critical|super_critical`)
- `combat_tags` (multi-tag string, `|`-separated)

New threat-classification variables:
- `threat_vector_primary` (for example `on_death_burst`, `ranged_burst`, `area_denial`, `debuff_control`, `spawn_pressure`)
- `threat_vector_secondary`
- `engagement_profile` (for example `sniper`, `rushdown_melee`, `support_spawner`, `suicide_rusher`)
- `mobility_class` (`stationary|slow_heavy|standard|kiting|fast`)
- `burst_pressure_rating` (`0-5`)
- `control_pressure_rating` (`0-5`)
- `attrition_pressure_rating` (`0-5`)
- `spawn_pressure_rating` (`0-5`)
- `threat_rollup_rating` (`0-5`)
- `threat_intensity_rating` (`0-6`)
- `human_consensus_score` (`0-100`)
- `human_consensus_band` (`routine|caution|dangerous|feared|run_ending`)
- `consensus_source_bucket` (`mechanics_inferred|community_dangerous|community_feared|community_run_ending`)
- `target_priority_score` (`0-100`)
- `avoidance_priority` (`True`/`False`)
- `needs_line_of_sight_break` (`True`/`False`)
- `needs_corpse_control` (`True`/`False`)
- `needs_debuff_response` (`True`/`False`)

Boolean convenience flags:
- `is_light_mover`
- `is_exploder`
- `is_archer` (alias for all ranged attackers)
- `is_ranged_attacker`
- `is_life_drain`
- `is_mana_drain`
- `is_viper_cloud`
- `is_frenzy_melee`
- `is_projectile_burst`
- `is_debuff_source`
- `is_critical_threat`
- `is_super_critical_threat`

Danger scale:
- `0`: non-combat target (ignore in combat planner)
- `1`: minimal danger
- `2`: low danger
- `3`: medium danger
- `4`: high danger
- `5`: critical danger
- `6`: super-critical danger

Current built-in categories/tags include:
- `ranged_attacker`, `archer`, `ranged_physical`, `ranged_magic`
- `melee_attacker`, `heavy_melee`, `frenzy_melee`, `leaper`
- `light_mover`, `explode`, `on_death_hazard`, `doll_exploder`
- `summoner`, `resurrector`, `corpse_or_spawn_pressure`
- `curse`, `debuff_source`, `crowd_control`
- `life_drain`, `mana_drain`
- `elemental_fire`, `elemental_cold`, `elemental_lightning`, `elemental_poison`
- `lightning_sniper`, `projectile_burst`, `viper_cloud`
- `turret`, `aura_scaling`, `elite_unique`, `superunique`, `act_boss`, `high_threat`
- `critical_threat`, `super_critical_threat`

Consensus grounding:
- `super_critical` is intentionally narrow and maps to community-consensus run-ending threats (dolls/soul-lightning variants)
- `critical` includes explicit high-risk mechanics (viper cloud family, frenzytaur family, oblivion knights, act bosses) plus strict elite combinations
- `human_consensus_score` and bands are deterministic, source-backed priors from community discussions plus mechanics weighting
- full rationale and source links are in `THREAT_CONSENSUS.md`

Notes on "final" categorization:
- tags and ratings are generated from current seed fields (`monstats_id`, `display_name`, `name_str`, `base_id`, `mon_type`, `ai`, `threat`, `superunique_refs`)
- this is production-ready for deterministic behavior and tuning loops, but still heuristic (not a trained labeled model)
- if you later add live aura/affix OCR, you can stack those on top of `target_priority_score` and `avoidance_priority`

This gives enemy detection, target selection, and avoidance logic direct hooks (for example prioritize `super_critical` targets while also triggering `needs_line_of_sight_break`/`needs_corpse_control` safeguards).
