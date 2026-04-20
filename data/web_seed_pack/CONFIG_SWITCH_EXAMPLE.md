# Config Switch Example

Use this pack now, then comment it out later when you switch to your own data.

## Use Web Seed Pack

In `bot/config.py` (or your runtime override layer), point to:

- `pickit_db_path = Path("data/web_seed_pack/processed/pickit/default_pickit.web_seed.json")`

Optional references for tooling:

- monster index seed: `data/web_seed_pack/processed/monsters/monster_index.web_seed.csv`
- monster catalog seed: `data/web_seed_pack/processed/monsters/monster_catalog.web_seed.jsonl`
- item catalog seed: `data/web_seed_pack/processed/items/item_catalog.web_seed.csv`

## Disable Web Seed Pack Later

When you move to your own captures/data:

1. Switch `pickit_db_path` back to your own file (for example `data/pickit/default_pickit.json`).
2. Stop reading any `data/web_seed_pack/...` files in training/import scripts.
3. Optionally archive or remove this entire folder.