"""Pickit database loader and matcher for ground item pickup logic."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from bot.game_state import GroundItemDetection, PickitMatch


@dataclass(frozen=True)
class PickitRule:
    name: str
    contains: Tuple[str, ...]
    priority: int = 50
    enabled: bool = True


class PickitDatabase:
    def __init__(
        self,
        rules: Sequence[PickitRule],
        pickup_gold: bool = True,
        min_gold_amount: int = 400,
        gold_priority: int = 35,
    ):
        """Initialize a new `PickitDatabase` instance.

        Parameters:
            rules: Parameter for rules used in this routine.
            pickup_gold: Parameter for pickup gold used in this routine.
            min_gold_amount: Parameter for min gold amount used in this routine.
            gold_priority: Parameter for gold priority used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.rules = tuple(rules)
        self.pickup_gold = bool(pickup_gold)
        self.min_gold_amount = max(0, int(min_gold_amount))
        self.gold_priority = int(gold_priority)

    @classmethod
    def default(cls) -> "PickitDatabase":
        """Default.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `'PickitDatabase'`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return cls(
            rules=(
                PickitRule(name="runes", contains=("rune",), priority=95),
                PickitRule(name="keys", contains=("key",), priority=85),
                PickitRule(name="potions_rejuv", contains=("rejuvenation",), priority=82),
                PickitRule(name="potions_heal", contains=("healing", "heal"), priority=70),
                PickitRule(name="potions_mana", contains=("mana",), priority=68),
                PickitRule(name="gems", contains=("gem", "skull"), priority=66),
                PickitRule(name="charms", contains=("charm",), priority=76),
            ),
            pickup_gold=True,
            min_gold_amount=400,
            gold_priority=35,
        )

    @classmethod
    def load(cls, path: Path, logger: logging.Logger | None = None) -> "PickitDatabase":
        """Load.

        Parameters:
            path: Parameter for path used in this routine.
            logger: Parameter used to emit diagnostic log messages.

        Local Variables:
            contains: Local variable for contains used in this routine.
            payload: Local variable for payload used in this routine.
            raw: Local variable for raw used in this routine.
            rules: Local variable for rules used in this routine.

        Returns:
            A value matching the annotated return type `'PickitDatabase'`.

        Side Effects:
            - May mutate mutable containers or objects in place.
            - May perform I/O or logging through called dependencies.
        """
        if not path.exists():
            if logger is not None:
                logger.warning("Pickit database not found at %s. Using built-in defaults.", path)
            return cls.default()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            if logger is not None:
                logger.warning("Failed to parse pickit database at %s (%s). Using built-in defaults.", path, exc)
            return cls.default()

        rules: List[PickitRule] = []
        for raw in payload.get("rules", []):
            contains = _normalize_tokens(raw.get("contains", ()))
            if not contains:
                continue

            rules.append(
                PickitRule(
                    name=str(raw.get("name", "rule")).strip() or "rule",
                    contains=contains,
                    priority=int(raw.get("priority", 50)),
                    enabled=bool(raw.get("enabled", True)),
                )
            )

        if not rules:
            if logger is not None:
                logger.warning("Pickit database at %s has no valid rules. Using built-in defaults.", path)
            return cls.default()

        return cls(
            rules=tuple(rules),
            pickup_gold=bool(payload.get("pickup_gold", True)),
            min_gold_amount=int(payload.get("min_gold_amount", 400)),
            gold_priority=int(payload.get("gold_priority", 35)),
        )

    def match_detection(self, detection: GroundItemDetection) -> PickitMatch | None:
        """Match detection.

        Parameters:
            detection: Parameter for detection used in this routine.

        Local Variables:
            best: Local variable for best used in this routine.
            candidate: Local variable for candidate used in this routine.
            label: Local variable for label used in this routine.
            rule: Local variable for rule used in this routine.
            token: Local variable for token used in this routine.

        Returns:
            A value matching the annotated return type `PickitMatch | None`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if detection.is_gold:
            if self.pickup_gold and detection.gold_amount >= self.min_gold_amount:
                return PickitMatch(item=detection, priority=self.gold_priority, rule_name="gold")
            return None

        label = (detection.label or "").strip().lower()
        if not label:
            return None

        best: PickitMatch | None = None
        for rule in self.rules:
            if not rule.enabled:
                continue

            if any(token in label for token in rule.contains):
                candidate = PickitMatch(item=detection, priority=rule.priority, rule_name=rule.name)
                if best is None or candidate.priority > best.priority:
                    best = candidate

        return best

    def pick_candidates(self, detections: Iterable[GroundItemDetection]) -> List[PickitMatch]:
        """Pick candidates.

        Parameters:
            detections: Parameter for detections used in this routine.

        Local Variables:
            detection: Local variable for detection used in this routine.
            matched: Local variable for matched used in this routine.
            matches: Local variable for matches used in this routine.

        Returns:
            A value matching the annotated return type `List[PickitMatch]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        matches: List[PickitMatch] = []
        for detection in detections:
            matched = self.match_detection(detection)
            if matched is not None:
                matches.append(matched)

        matches.sort(key=lambda m: (-m.priority, -m.item.confidence, m.item.label.lower()))
        return matches


def _normalize_tokens(value: object) -> Tuple[str, ...]:
    """Internal helper to normalize tokens.

    Parameters:
        value: Parameter for value used in this routine.

    Local Variables:
        normalized: Local variable for normalized used in this routine.
        raw: Local variable for raw used in this routine.
        token: Local variable for token used in this routine.
        tokens: Local variable for tokens used in this routine.
        v: Local variable for v used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[str, ...]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    if isinstance(value, str):
        raw = [value]
    elif isinstance(value, (list, tuple)):
        raw = [str(v) for v in value]
    else:
        raw = []

    tokens = []
    for token in raw:
        normalized = token.strip().lower()
        if normalized:
            tokens.append(normalized)

    return tuple(tokens)