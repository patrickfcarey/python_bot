"""Validate monster dataset coverage against monster_index targets.

Example:
python scripts/validate_monster_dataset.py --fail-on-missing
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
NAME_PATTERN = re.compile(r"^(hover|body)__([a-z0-9_]+)__")


def collect_files(root: Path) -> Iterable[Path]:
    """Collect files.

    Parameters:
        root: Parameter for root used in this routine.

    Local Variables:
        path: Local variable for path used in this routine.

    Returns:
        A value matching the annotated return type `Iterable[Path]`.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS
    ]


def count_by_slug(files: Iterable[Path], prefix: str) -> Dict[str, int]:
    """Count by slug.

    Parameters:
        files: Parameter for files used in this routine.
        prefix: Parameter for prefix used in this routine.

    Local Variables:
        counts: Local variable tracking how many items are present or processed.
        file_path: Local variable containing a filesystem location.
        kind: Local variable for kind used in this routine.
        match: Local variable for match used in this routine.
        slug: Local variable for slug used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, int]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    counts: Dict[str, int] = {}
    for file_path in files:
        match = NAME_PATTERN.match(file_path.stem)
        if not match:
            continue
        kind, slug = match.groups()
        if kind != prefix:
            continue
        counts[slug] = counts.get(slug, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    """Parse args.

    Parameters:
        None.

    Local Variables:
        parser: Local variable for parser used in this routine.
        script_root: Local variable for script root used in this routine.

    Returns:
        A value matching the annotated return type `argparse.Namespace`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    script_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Validate monster dataset coverage")
    parser.add_argument(
        "--repo-root",
        default=str(script_root),
        help="Repo root path (default: parent of scripts directory)",
    )
    parser.add_argument(
        "--index-file",
        default="data/monsters/labels/monster_index.template.csv",
        help="CSV index file with target counts",
    )
    parser.add_argument(
        "--hover-dir",
        default="data/monsters/raw/in_game/hover_name_bar",
        help="Directory containing hover-name images",
    )
    parser.add_argument(
        "--body-dir",
        default="data/monsters/raw/in_game/body_crops",
        help="Directory containing body-crop images",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional JSON report output path",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit non-zero if any monster is under target",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, path_value: str) -> Path:
    """Resolve path.

    Parameters:
        repo_root: Parameter for repo root used in this routine.
        path_value: Parameter for path value used in this routine.

    Local Variables:
        candidate: Local variable for candidate used in this routine.

    Returns:
        A value matching the annotated return type `Path`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def main() -> int:
    """Main.

    Parameters:
        None.

    Local Variables:
        args: Local variable for args used in this routine.
        body_counts: Local variable tracking how many items are present or processed.
        body_dir: Local variable containing a filesystem location.
        body_ok: Local variable for body ok used in this routine.
        body_str: Local variable for body str used in this routine.
        complete: Local variable for complete used in this routine.
        display_name: Local variable for display name used in this routine.
        found_body: Local variable for found body used in this routine.
        found_hover: Local variable for found hover used in this routine.
        handle: Local variable for handle used in this routine.
        hover_counts: Local variable tracking how many items are present or processed.
        hover_dir: Local variable containing a filesystem location.
        hover_ok: Local variable for hover ok used in this routine.
        hover_str: Local variable for hover str used in this routine.
        incomplete_rows: Local variable for incomplete rows used in this routine.
        index_path: Local variable containing a filesystem location.
        monster_id: Local variable for monster id used in this routine.
        output_path: Local variable containing a filesystem location.
        payload: Local variable for payload used in this routine.
        reader: Local variable for reader used in this routine.
        repo_root: Local variable for repo root used in this routine.
        report_rows: Local variable for report rows used in this routine.
        row: Local variable for row used in this routine.
        slug: Local variable for slug used in this routine.
        status: Local variable for status used in this routine.
        target_body: Local variable for target body used in this routine.
        target_hover: Local variable for target hover used in this routine.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    index_path = resolve_path(repo_root, args.index_file)
    hover_dir = resolve_path(repo_root, args.hover_dir)
    body_dir = resolve_path(repo_root, args.body_dir)

    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")

    hover_counts = count_by_slug(collect_files(hover_dir), prefix="hover")
    body_counts = count_by_slug(collect_files(body_dir), prefix="body")

    report_rows: List[Dict[str, object]] = []
    with index_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            slug = (row.get("slug") or "").strip()
            monster_id = (row.get("monster_id") or "").strip()
            display_name = (row.get("display_name") or "").strip()

            target_hover = int((row.get("target_hover_images") or "0").strip() or "0")
            target_body = int((row.get("target_body_images") or "0").strip() or "0")

            found_hover = hover_counts.get(slug, 0)
            found_body = body_counts.get(slug, 0)

            hover_ok = found_hover >= target_hover
            body_ok = found_body >= target_body
            complete = hover_ok and body_ok

            report_rows.append(
                {
                    "monster_id": monster_id,
                    "slug": slug,
                    "display_name": display_name,
                    "target_hover_images": target_hover,
                    "found_hover_images": found_hover,
                    "target_body_images": target_body,
                    "found_body_images": found_body,
                    "missing_hover_images": max(0, target_hover - found_hover),
                    "missing_body_images": max(0, target_body - found_body),
                    "complete": complete,
                }
            )

    if not report_rows:
        print("No monsters found in index file.")
        return 1

    incomplete_rows = [row for row in report_rows if not row["complete"]]

    print("monster_id\tslug\thover\tbody\tstatus")
    for row in report_rows:
        hover_str = f"{row['found_hover_images']}/{row['target_hover_images']}"
        body_str = f"{row['found_body_images']}/{row['target_body_images']}"
        status = "OK" if row["complete"] else "MISSING"
        print(f"{row['monster_id']}\t{row['slug']}\t{hover_str}\t{body_str}\t{status}")

    print("")
    print(f"Total monsters: {len(report_rows)}")
    print(f"Complete: {len(report_rows) - len(incomplete_rows)}")
    print(f"Missing: {len(incomplete_rows)}")

    if args.output_json:
        output_path = resolve_path(repo_root, args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "index_file": str(index_path),
            "hover_dir": str(hover_dir),
            "body_dir": str(body_dir),
            "total_monsters": len(report_rows),
            "complete_monsters": len(report_rows) - len(incomplete_rows),
            "missing_monsters": len(incomplete_rows),
            "rows": report_rows,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        print(f"Wrote JSON report: {output_path}")

    if args.fail_on_missing and incomplete_rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
