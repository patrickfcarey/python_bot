"""Chat-command OCR parser and runtime control dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time
from typing import Iterable, List, Optional, Sequence, Tuple

from bot.command_module import CommandModule
from bot.config import RuntimeConfig
from bot.controller import Action


_CHAT_LINE_PATTERN = re.compile(
    r"^\s*(?:(?P<sender>[A-Za-z0-9_\-\[\] ]{1,32})\s*[:>]\s*)?(?P<body>.+?)\s*$"
)


@dataclass(frozen=True)
class ChatCommandEvent:
    """One parsed chat command event."""

    sender: str
    command: str
    argument: str
    raw_line: str
    confidence: float
    accepted: bool
    reason: str


@dataclass(frozen=True)
class ChatCommandStats:
    """Runtime counters for chat-command ingestion behavior."""

    poll_count: int
    scanned_lines: int
    parsed_commands: int
    accepted_commands: int
    rejected_commands: int
    duplicate_drops: int
    low_confidence_drops: int


class ChatCommandProcessor:
    """Polls OCR chat lines, parses commands, and applies runtime overrides."""

    def __init__(self, config: RuntimeConfig, logger: Optional[logging.Logger] = None):
        self._config = config
        self._logger = logger if logger is not None else logging.getLogger("python_bot.chat_commands")

        self._enabled = bool(config.chat_commands_enabled)
        self._prefix = str(config.chat_command_prefix).strip()
        self._poll_interval_s = max(0.05, float(config.chat_command_poll_interval_s))
        self._dedupe_window_s = max(0.0, float(config.chat_command_dedupe_window_s))
        self._min_confidence = float(config.chat_command_ocr_confidence_threshold)
        self._max_actions_per_poll = max(1, int(config.chat_command_max_actions_per_poll))

        self._require_sender = bool(config.chat_command_require_sender)
        self._allow_no_prefix = bool(config.chat_command_allow_no_prefix)
        self._allowed_senders = {
            self._normalize_sender(sender)
            for sender in config.chat_command_allowed_senders
            if self._normalize_sender(sender)
        }

        self._last_poll_monotonic = 0.0
        self._recent_signatures = {}

        self._poll_count = 0
        self._scanned_lines = 0
        self._parsed_commands = 0
        self._accepted_commands = 0
        self._rejected_commands = 0
        self._duplicate_drops = 0
        self._low_confidence_drops = 0

    @property
    def enabled(self) -> bool:
        """Return whether chat command processing is enabled."""
        return bool(self._enabled)

    def poll_and_apply(self, vision, frame, commands: CommandModule, now_monotonic: Optional[float] = None) -> List[ChatCommandEvent]:
        """Poll OCR chat lines from frame and apply any accepted commands."""
        if not self._enabled:
            return []

        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        if (now - self._last_poll_monotonic) < self._poll_interval_s:
            return []

        self._last_poll_monotonic = now
        self._poll_count += 1

        lines: Sequence[Tuple[str, float]] = vision.scan_chat_lines(
            frame,
            max_lines=int(self._config.chat_command_max_lines),
        )
        self._scanned_lines += len(lines)
        return self.ingest_lines(lines=lines, commands=commands, now_monotonic=now)

    def ingest_lines(
        self,
        lines: Iterable[Tuple[str, float]],
        commands: CommandModule,
        now_monotonic: Optional[float] = None,
    ) -> List[ChatCommandEvent]:
        """Ingest pre-read OCR chat lines and apply accepted commands."""
        if not self._enabled:
            return []

        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        events: List[ChatCommandEvent] = []
        accepted_this_poll = 0

        self._gc_recent_signatures(now)

        for raw_line, confidence in lines:
            if accepted_this_poll >= self._max_actions_per_poll:
                break

            confidence_value = float(confidence)
            if confidence_value < self._min_confidence:
                self._low_confidence_drops += 1
                continue

            parsed = self._parse_command_candidate(str(raw_line))
            if parsed is None:
                continue

            sender_name, command_name, argument_text = parsed
            self._parsed_commands += 1

            allowed, sender_reason = self._is_sender_allowed(sender_name)
            if not allowed:
                self._rejected_commands += 1
                events.append(
                    ChatCommandEvent(
                        sender=sender_name,
                        command=command_name,
                        argument=argument_text,
                        raw_line=str(raw_line),
                        confidence=confidence_value,
                        accepted=False,
                        reason=sender_reason,
                    )
                )
                continue

            signature = self._make_signature(sender_name, command_name, argument_text)
            if self._is_duplicate_signature(signature, now):
                self._duplicate_drops += 1
                continue

            accepted, reason = self._apply_command(
                commands=commands,
                command_name=command_name,
                argument_text=argument_text,
            )
            if accepted:
                accepted_this_poll += 1
                self._accepted_commands += 1
            else:
                self._rejected_commands += 1

            event = ChatCommandEvent(
                sender=sender_name,
                command=command_name,
                argument=argument_text,
                raw_line=str(raw_line),
                confidence=confidence_value,
                accepted=accepted,
                reason=reason,
            )
            events.append(event)

            if accepted:
                self._recent_signatures[signature] = now
                self._logger.info(
                    "Chat command accepted sender=%s command=%s arg=%s",
                    sender_name or "unknown",
                    command_name,
                    argument_text,
                )

        return events

    def stats(self) -> ChatCommandStats:
        """Return immutable chat-command runtime counters."""
        return ChatCommandStats(
            poll_count=int(self._poll_count),
            scanned_lines=int(self._scanned_lines),
            parsed_commands=int(self._parsed_commands),
            accepted_commands=int(self._accepted_commands),
            rejected_commands=int(self._rejected_commands),
            duplicate_drops=int(self._duplicate_drops),
            low_confidence_drops=int(self._low_confidence_drops),
        )

    def _parse_command_candidate(self, raw_line: str) -> Optional[Tuple[str, str, str]]:
        """Parse one OCR line into `(sender, command, argument)` when possible."""
        line_text = str(raw_line or "").strip()
        if not line_text:
            return None

        match = _CHAT_LINE_PATTERN.match(line_text)
        if match is None:
            return None

        sender = str(match.group("sender") or "").strip()
        body = str(match.group("body") or "").strip()
        if not body:
            return None

        command_body = body
        if self._prefix:
            prefix_idx = body.find(self._prefix)
            if prefix_idx >= 0:
                command_body = body[prefix_idx + len(self._prefix) :].strip()
            elif not self._allow_no_prefix:
                return None

        if not command_body:
            return None

        tokens = command_body.split()
        if not tokens:
            return None

        command_name = str(tokens[0]).strip().lower()
        argument_text = " ".join(tokens[1:]).strip().lower()
        return (sender, command_name, argument_text)

    def _is_sender_allowed(self, sender: str) -> Tuple[bool, str]:
        """Check whether command sender passes configured filters."""
        sender_norm = self._normalize_sender(sender)

        if self._require_sender and not sender_norm:
            return (False, "sender_required")

        if self._allowed_senders and sender_norm not in self._allowed_senders:
            return (False, "sender_not_allowed")

        return (True, "ok")

    @staticmethod
    def _normalize_sender(sender: str) -> str:
        """Normalize sender token for case-insensitive matching."""
        return str(sender or "").strip().casefold()

    @staticmethod
    def _make_signature(sender: str, command_name: str, argument_text: str) -> str:
        """Build dedupe signature for one parsed command."""
        return "|".join(
            [
                ChatCommandProcessor._normalize_sender(sender),
                str(command_name or "").strip().lower(),
                str(argument_text or "").strip().lower(),
            ]
        )

    def _is_duplicate_signature(self, signature: str, now_monotonic: float) -> bool:
        """Check dedupe cache to suppress repeated OCR command echoes."""
        if self._dedupe_window_s <= 0.0:
            return False

        last_seen = self._recent_signatures.get(signature)
        if last_seen is None:
            return False
        return (now_monotonic - float(last_seen)) < self._dedupe_window_s

    def _gc_recent_signatures(self, now_monotonic: float):
        """Evict stale dedupe entries to keep memory bounded."""
        if not self._recent_signatures:
            return

        ttl = max(1.0, self._dedupe_window_s * 2.0)
        stale_keys = [
            key
            for key, seen_at in self._recent_signatures.items()
            if (now_monotonic - float(seen_at)) > ttl
        ]
        for key in stale_keys:
            self._recent_signatures.pop(key, None)

    def _apply_command(self, commands: CommandModule, command_name: str, argument_text: str) -> Tuple[bool, str]:
        """Apply one parsed command into queue or persistent runtime overrides."""
        verb = str(command_name or "").strip().lower()
        arg = str(argument_text or "").strip().lower()

        if verb in {"stop", "pause", "hold"}:
            commands.set_paused(True)
            commands.add_command(Action(stop=True, reason="chat_cmd_stop"))
            return (True, "paused")

        if verb in {"follow", "resume", "go"}:
            if arg in {"off", "false", "0"}:
                commands.set_paused(True)
                commands.add_command(Action(stop=True, reason="chat_cmd_follow_off"))
                return (True, "follow_disabled")

            commands.set_paused(False)
            commands.add_command(Action(hold_move=False, reason="chat_cmd_follow_on"))
            return (True, "follow_enabled")

        if verb in {"combat", "pickup", "potion", "potions"}:
            toggle_value = self._parse_toggle_argument(arg)
            if toggle_value is None and arg not in {"", "auto", "default", "reset"}:
                return (False, "invalid_toggle_arg")

            if verb == "combat":
                commands.set_combat_enabled_override(toggle_value)
                return (True, "combat_override_set")
            if verb == "pickup":
                commands.set_pickup_enabled_override(toggle_value)
                return (True, "pickup_override_set")

            commands.set_potion_enabled_override(toggle_value)
            return (True, "potion_override_set")

        if verb == "cast":
            slot = str(arg).strip().replace(" ", "_")
            if not slot:
                return (False, "missing_cast_slot")

            commands.add_command(Action(cast_spell=slot, reason=f"chat_cmd_cast_{slot}"))
            return (True, "cast_queued")

        if verb in {"town", "tp"}:
            commands.add_command(Action(cast_spell="town_portal", reason="chat_cmd_town_portal"))
            return (True, "town_portal_queued")

        if verb in {"reset", "auto"}:
            commands.reset_overrides()
            return (True, "overrides_reset")

        if verb == "status":
            return (True, "status_ack")

        return (False, "unknown_command")

    @staticmethod
    def _parse_toggle_argument(argument_text: str) -> Optional[bool]:
        """Parse toggle argument to bool (`None` means auto/default)."""
        value = str(argument_text or "").strip().lower()
        if value in {"", "auto", "default", "reset"}:
            return None
        if value in {"on", "true", "1", "enable", "enabled", "yes"}:
            return True
        if value in {"off", "false", "0", "disable", "disabled", "no"}:
            return False
        return None
