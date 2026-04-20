# Web Seed Pack

This folder is a self-contained web-sourced seed dataset for `python_bot`.

Generated at: 2026-04-16T02:50:27+00:00

## What Is Included

- Arreat Summit monster listing/detail pages (raw HTML)
- Arreat Summit bestiary animation images downloaded locally
- Normalized monster outputs:
  - `processed/monsters/monster_catalog.web_seed.jsonl`
  - `processed/monsters/monster_index.web_seed.csv`
  - `processed/monsters/monster_image_urls.csv`
- d2data raw JSON snapshots
- Normalized item outputs:
  - `processed/items/item_catalog.web_seed.csv`
  - `processed/items/item_names.web_seed.txt`
- Pickit starter:
  - `processed/pickit/default_pickit.web_seed.json`

## Disable/Replace Later

- Keep this entire folder separate and point runtime to your own sources when ready.
- For pickit, switch `RuntimeConfig.pickit_db_path` to your preferred file.
- For monster OCR/vision training, replace with your in-game captures per `MONSTER_DATA_STRUCTURE.md`.

## Source URLs

- Arreat Summit: `https://classic.battle.net/diablo2exp/monsters/`
- d2data repo: `https://github.com/blizzhackers/d2data`

- d2data monster universe:
  - processed/monsters/d2data_monstats.web_seed.csv`r
  - processed/monsters/d2data_superuniques.web_seed.csv`r

- rebuild script copy: scripts/build_web_seed_pack.py`r
- config switch guide: CONFIG_SWITCH_EXAMPLE.md`r
