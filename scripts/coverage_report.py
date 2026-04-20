"""Build a scenario-coverage report from observer event JSONL logs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bot.coverage import ScenarioCoverageTracker


def _resolve_input_paths(input_value: str) -> Iterable[Path]:
    """Resolve input path or glob into sorted JSONL file list."""
    input_text = str(input_value).strip()
    if not input_text:
        default_dir = Path("logs/observer")
        if not default_dir.exists():
            return []
        return sorted(default_dir.glob("observer_events_*.jsonl"))

    candidate_path = Path(input_text)
    if candidate_path.is_file():
        return [candidate_path]

    if candidate_path.is_dir():
        return sorted(candidate_path.glob("observer_events_*.jsonl"))

    # Treat unknown input as glob expression.
    return sorted(Path(".").glob(input_text))


def build_parser() -> argparse.ArgumentParser:
    """Create command-line parser for coverage reporting."""
    parser = argparse.ArgumentParser(description="Generate observer scenario-coverage report")
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="Input JSONL file, directory, or glob. Default: logs/observer/observer_events_*.jsonl",
    )
    parser.add_argument(
        "--target-per-bucket",
        type=int,
        default=300,
        help="Target samples per scenario bucket used for deficit calculations",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="How many underfilled buckets to display",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional output report path. Default: logs/observer/coverage_report_UTC.json",
    )
    return parser


def main():
    """Read observer events, aggregate scenario coverage, and emit report."""
    parser = build_parser()
    args = parser.parse_args()

    input_paths = list(_resolve_input_paths(args.input))
    if not input_paths:
        raise SystemExit("No observer event files found for coverage reporting.")

    tracker = ScenarioCoverageTracker(target_per_bucket=max(1, int(args.target_per_bucket)))
    total_lines = 0
    parse_errors = 0

    for input_path in input_paths:
        with input_path.open("r", encoding="utf-8") as handle:
            for line_text in handle:
                line_value = line_text.strip()
                if not line_value:
                    continue

                total_lines += 1
                try:
                    payload = json.loads(line_value)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue

                scenario_tags = payload.get("scenario_tags", {})
                if not isinstance(scenario_tags, dict):
                    scenario_tags = {}
                tracker.update(scenario_tags)

    summary = tracker.summary(top_n=max(1, int(args.top)))
    report_payload = summary.to_dict()
    report_payload["input_files"] = [str(path) for path in input_paths]
    report_payload["input_lines"] = int(total_lines)
    report_payload["parse_errors"] = int(parse_errors)
    report_payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if args.output_json:
        output_path = Path(args.output_json)
    else:
        output_dir = Path("logs/observer")
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"coverage_report_{stamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report_payload, handle, indent=2, sort_keys=True)

    print(f"Coverage report written: {output_path}")
    print(f"Input files: {len(input_paths)} | lines: {total_lines} | parse_errors: {parse_errors}")
    print(
        "Coverage: "
        f"total_events={summary.total_events} unique_buckets={summary.unique_buckets} "
        f"under_target_buckets={summary.under_target_buckets}"
    )


if __name__ == "__main__":
    main()
