"""Build a self-contained web-seeded data pack for python_bot.

Outputs everything into a single folder so it can be disabled/replaced later.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ARREAT_BASE = "https://classic.battle.net/diablo2exp/monsters/"
D2DATA_BASE = "https://raw.githubusercontent.com/blizzhackers/d2data/master/json/"

LISTING_PAGES: Dict[str, str] = {
    "act1": "act1.shtml",
    "act2": "act2.shtml",
    "act3": "act3.shtml",
    "act4": "act4.shtml",
    "act5": "act5.shtml",
    "super": "super.shtml",
    "bosses": "bosses.shtml",
}

D2DATA_FILES = (
    "allstrings-eng.json",
    "monstats.json",
    "superuniques.json",
    "levels.json",
    "misc.json",
    "armor.json",
    "weapons.json",
)


@dataclass(frozen=True)
class MonsterPageRef:
    category: str
    href: str
    display_name: str
    detail_url: str


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "python_bot_web_seed_builder/1.0"})
    with urlopen(req, timeout=60) as response:
        return response.read()


def fetch_text(url: str) -> str:
    raw = fetch_bytes(url)
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_anchor_links(html: str) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    for href, text_html in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        text = re.sub(r"<[^>]+>", "", text_html)
        text = re.sub(r"\s+", " ", text).strip()
        links.append((href.strip(), text))
    return links


def collect_arreat_refs(raw_listing_dir: Path) -> List[MonsterPageRef]:
    nav_pages = set(LISTING_PAGES.values()) | {"basics.shtml", "bonus.shtml", "bosses.shtml", "super.shtml"}
    refs: Dict[str, MonsterPageRef] = {}

    for category, page in LISTING_PAGES.items():
        url = urljoin(ARREAT_BASE, page)
        html = fetch_text(url)
        (raw_listing_dir / page).write_text(html, encoding="utf-8")

        for href, text in parse_anchor_links(html):
            href = href.split("#", 1)[0].strip()
            if not href.lower().endswith(".shtml"):
                continue
            if href.startswith("/") or "://" in href.lower():
                continue
            if href in nav_pages:
                continue
            if not text:
                continue
            if text.lower().startswith("act "):
                continue
            if text in {"Monsters", "Bonuses", "Boss Monsters", "Super Unique Monsters"}:
                continue

            detail_url = urljoin(ARREAT_BASE, href)
            refs[href] = MonsterPageRef(
                category=category,
                href=href,
                display_name=text,
                detail_url=detail_url,
            )

    return sorted(refs.values(), key=lambda r: (r.category, r.href))


def extract_arreat_image_urls(detail_html: str) -> List[str]:
    matches = re.findall(
        r'"(/images/battle/diablo2exp/images/animations/bestiary/[^"]+\.(?:gif|jpg|png))"',
        detail_html,
        flags=re.I,
    )
    deduped: List[str] = []
    seen = set()
    for m in matches:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    return deduped


def build_arreat_bundle(root: Path) -> Dict[str, int]:
    raw_listing_dir = root / "raw" / "arreat" / "listing_pages"
    raw_detail_dir = root / "raw" / "arreat" / "detail_pages"
    raw_image_dir = root / "raw" / "arreat" / "images"
    processed_dir = root / "processed" / "monsters"

    for path in (raw_listing_dir, raw_detail_dir, raw_image_dir, processed_dir):
        path.mkdir(parents=True, exist_ok=True)

    refs = collect_arreat_refs(raw_listing_dir)

    source_rows: List[Dict[str, str]] = []
    image_rows: List[Dict[str, str]] = []
    catalog_rows: List[Dict[str, object]] = []
    index_rows: List[Dict[str, object]] = []

    downloaded_images = 0
    total_image_refs = 0

    for idx, ref in enumerate(refs, start=1):
        detail_html = fetch_text(ref.detail_url)
        detail_path = raw_detail_dir / f"{idx:04d}__{Path(ref.href).name}.html"
        detail_path.write_text(detail_html, encoding="utf-8")

        title_match = re.search(r"<title>(.*?)</title>", detail_html, flags=re.I | re.S)
        page_title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ref.display_name

        href_stem = Path(ref.href).stem
        monster_slug = slugify(ref.display_name)
        monster_id = f"web_{monster_slug}"

        image_urls = [urljoin("https://classic.battle.net", rel) for rel in extract_arreat_image_urls(detail_html)]
        total_image_refs += len(image_urls)

        local_image_paths: List[str] = []
        for img_idx, image_url in enumerate(image_urls, start=1):
            ext = Path(image_url).suffix.lower() or ".gif"
            image_name = f"arreat__{monster_slug}__variant{img_idx:03d}__idx0001{ext}"
            local_path = raw_image_dir / image_name

            if not local_path.exists():
                local_path.write_bytes(fetch_bytes(image_url))
                downloaded_images += 1

            local_rel = local_path.relative_to(root).as_posix()
            local_image_paths.append(local_rel)

            image_rows.append(
                {
                    "monster_id": monster_id,
                    "slug": monster_slug,
                    "display_name": ref.display_name,
                    "category": ref.category,
                    "detail_url": ref.detail_url,
                    "image_url": image_url,
                    "local_path": local_rel,
                }
            )

        act_num = 0
        if ref.category.startswith("act") and ref.category[3:].isdigit():
            act_num = int(ref.category[3:])

        is_boss = ref.category in {"super", "bosses"}
        target_hover = 50 if is_boss else 25
        target_body = 80 if is_boss else 40

        catalog_rows.append(
            {
                "monster_id": monster_id,
                "slug": monster_slug,
                "display_name": ref.display_name,
                "family": monster_slug.split("_")[0],
                "acts": [act_num] if act_num else [],
                "areas": [],
                "is_boss": is_boss,
                "is_minion": False,
                "source_refs": [ref.detail_url],
                "web_seed": {
                    "category": ref.category,
                    "href": ref.href,
                    "page_title": page_title,
                    "image_count": len(image_urls),
                    "local_images": local_image_paths,
                },
            }
        )

        index_rows.append(
            {
                "monster_id": monster_id,
                "slug": monster_slug,
                "display_name": ref.display_name,
                "target_hover_images": target_hover,
                "target_body_images": target_body,
                "covered": False,
            }
        )

        source_rows.append(
            {
                "category": ref.category,
                "href": ref.href,
                "display_name": ref.display_name,
                "detail_url": ref.detail_url,
                "detail_page_local": detail_path.relative_to(root).as_posix(),
            }
        )

    write_csv(
        processed_dir / "source_page_index.csv",
        source_rows,
        ["category", "href", "display_name", "detail_url", "detail_page_local"],
    )
    write_csv(
        processed_dir / "monster_image_urls.csv",
        image_rows,
        ["monster_id", "slug", "display_name", "category", "detail_url", "image_url", "local_path"],
    )
    write_csv(
        processed_dir / "monster_index.web_seed.csv",
        index_rows,
        ["monster_id", "slug", "display_name", "target_hover_images", "target_body_images", "covered"],
    )

    catalog_path = processed_dir / "monster_catalog.web_seed.jsonl"
    with catalog_path.open("w", encoding="utf-8") as handle:
        for row in catalog_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "arreat_monster_refs": len(refs),
        "arreat_detail_pages": len(source_rows),
        "arreat_total_image_refs": total_image_refs,
        "arreat_images_downloaded": downloaded_images,
    }


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_d2data_bundle(root: Path) -> Dict[str, int]:
    raw_dir = root / "raw" / "d2data"
    processed_items_dir = root / "processed" / "items"
    processed_pickit_dir = root / "processed" / "pickit"

    for path in (raw_dir, processed_items_dir, processed_pickit_dir):
        path.mkdir(parents=True, exist_ok=True)

    loaded: Dict[str, object] = {}
    for fn in D2DATA_FILES:
        text = fetch_text(urljoin(D2DATA_BASE, fn))
        (raw_dir / fn).write_text(text, encoding="utf-8")
        loaded[fn] = json.loads(text)

    item_rows: List[Dict[str, object]] = []
    item_names: List[str] = []

    for source_file, item_class in (("misc.json", "misc"), ("armor.json", "armor"), ("weapons.json", "weapons")):
        payload = loaded[source_file]
        if not isinstance(payload, dict):
            continue

        for code, row in payload.items():
            if not isinstance(row, dict):
                continue

            name = str(row.get("name") or "").strip()
            if not name:
                continue

            namestr = str(row.get("namestr") or "").strip()
            type_code = str(row.get("type") or "").strip()
            level_raw = row.get("level", 0)
            try:
                level = int(level_raw)
            except Exception:
                level = 0

            item_rows.append(
                {
                    "code": code,
                    "name": name,
                    "item_class": item_class,
                    "type": type_code,
                    "level": level,
                    "source_file": source_file,
                    "namestr": namestr,
                }
            )
            item_names.append(name)

    item_rows.sort(key=lambda r: (str(r["name"]).lower(), str(r["code"]).lower()))

    write_csv(
        processed_items_dir / "item_catalog.web_seed.csv",
        item_rows,
        ["code", "name", "item_class", "type", "level", "source_file", "namestr"],
    )

    unique_item_names = sorted(set(item_names), key=lambda s: s.lower())
    (processed_items_dir / "item_names.web_seed.txt").write_text("\n".join(unique_item_names) + "\n", encoding="utf-8")

    pickit_payload = {
        "version": 1,
        "source": "web_seed_pack",
        "pickup_gold": True,
        "min_gold_amount": 400,
        "gold_priority": 35,
        "rules": [
            {"name": "runes", "contains": ["rune"], "priority": 95, "enabled": True},
            {"name": "keys", "contains": ["key"], "priority": 88, "enabled": True},
            {"name": "charms", "contains": ["charm"], "priority": 85, "enabled": True},
            {"name": "jewels", "contains": ["jewel"], "priority": 80, "enabled": True},
            {"name": "rejuvenation_potions", "contains": ["rejuvenation"], "priority": 78, "enabled": True},
            {"name": "healing_potions", "contains": ["healing potion", "healing"], "priority": 72, "enabled": True},
            {"name": "mana_potions", "contains": ["mana potion", "mana"], "priority": 70, "enabled": True},
            {"name": "gems", "contains": ["gem", "skull"], "priority": 68, "enabled": True},
            {"name": "organs", "contains": ["essence", "token", "key of", "baal's eye", "mephisto's brain", "diablo's horn"], "priority": 82, "enabled": True},
        ],
    }

    (processed_pickit_dir / "default_pickit.web_seed.json").write_text(
        json.dumps(pickit_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "d2data_json_files": len(D2DATA_FILES),
        "item_catalog_rows": len(item_rows),
        "unique_item_names": len(unique_item_names),
        "pickit_rules": len(pickit_payload["rules"]),
    }


def write_metadata(root: Path, stats: Dict[str, int]):
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    readme = f"""# Web Seed Pack

This folder is a self-contained web-sourced seed dataset for `python_bot`.

Generated at: {generated}

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
"""
    (root / "README.md").write_text(readme, encoding="utf-8")

    sources_md = """# Sources

- https://classic.battle.net/diablo2exp/monsters/
- https://classic.battle.net/diablo2exp/monsters/act1.shtml
- https://classic.battle.net/diablo2exp/monsters/act2.shtml
- https://classic.battle.net/diablo2exp/monsters/act3.shtml
- https://classic.battle.net/diablo2exp/monsters/act4.shtml
- https://classic.battle.net/diablo2exp/monsters/act5.shtml
- https://classic.battle.net/diablo2exp/monsters/super.shtml
- https://classic.battle.net/diablo2exp/monsters/bosses.shtml
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/allstrings-eng.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/monstats.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/superuniques.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/levels.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/misc.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/armor.json
- https://raw.githubusercontent.com/blizzhackers/d2data/master/json/weapons.json
"""
    (root / "SOURCES.md").write_text(sources_md, encoding="utf-8")

    manifest = {
        "generated_at_utc": generated,
        "root": root.as_posix(),
        "stats": stats,
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "data" / "web_seed_pack"
    out_root.mkdir(parents=True, exist_ok=True)

    stats: Dict[str, int] = {}
    stats.update(build_arreat_bundle(out_root))
    stats.update(build_d2data_bundle(out_root))
    write_metadata(out_root, stats)

    print("Web seed pack generated:", out_root)
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")


if __name__ == "__main__":
    main()