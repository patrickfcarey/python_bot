"""Tests for OCR in-game chat command parsing and dispatch."""

from dataclasses import replace

from bot.chat_commands import ChatCommandProcessor
from bot.command_module import CommandModule
from bot.config import default_config


def _processor_with_defaults(**overrides):
    cfg = replace(default_config(), **overrides)
    return ChatCommandProcessor(config=cfg)


def test_ingest_stop_command_pauses_and_queues_stop_action():
    processor = _processor_with_defaults(
        chat_commands_enabled=True,
        chat_command_prefix="!",
        chat_command_allow_no_prefix=False,
    )
    commands = CommandModule()

    events = processor.ingest_lines(
        lines=[("Leader: !stop", 92.0)],
        commands=commands,
        now_monotonic=1.0,
    )

    assert len(events) == 1
    assert events[0].accepted is True
    assert events[0].command == "stop"
    assert commands.is_paused() is True

    action = commands.get_next()
    assert action is not None
    assert action.stop is True
    assert action.reason == "chat_cmd_stop"


def test_sender_allowlist_rejects_unknown_sender():
    processor = _processor_with_defaults(
        chat_commands_enabled=True,
        chat_command_prefix="!",
        chat_command_require_sender=True,
        chat_command_allowed_senders=("leader",),
    )
    commands = CommandModule()

    events = processor.ingest_lines(
        lines=[("Stranger: !follow", 90.0)],
        commands=commands,
        now_monotonic=2.0,
    )

    assert len(events) == 1
    assert events[0].accepted is False
    assert events[0].reason == "sender_not_allowed"
    assert commands.get_next() is None


def test_duplicate_line_is_dropped_within_dedupe_window():
    processor = _processor_with_defaults(
        chat_commands_enabled=True,
        chat_command_prefix="!",
        chat_command_dedupe_window_s=1.0,
    )
    commands = CommandModule()

    first = processor.ingest_lines(
        lines=[("Leader: !combat off", 88.0)],
        commands=commands,
        now_monotonic=10.0,
    )
    second = processor.ingest_lines(
        lines=[("Leader: !combat off", 89.0)],
        commands=commands,
        now_monotonic=10.2,
    )

    assert len(first) == 1
    assert len(second) == 0
    assert processor.stats().duplicate_drops == 1


def test_toggle_and_cast_commands_apply_expected_changes():
    processor = _processor_with_defaults(
        chat_commands_enabled=True,
        chat_command_prefix="!",
        chat_command_allow_no_prefix=False,
    )
    commands = CommandModule()

    processor.ingest_lines(
        lines=[("Leader: !combat off", 93.0)],
        commands=commands,
        now_monotonic=20.0,
    )
    assert commands.is_combat_enabled(default_enabled=True) is False

    processor.ingest_lines(
        lines=[("Leader: !combat auto", 93.0)],
        commands=commands,
        now_monotonic=20.5,
    )
    assert commands.is_combat_enabled(default_enabled=True) is True

    processor.ingest_lines(
        lines=[("Leader: !cast curse", 93.0), ("Leader: !tp", 93.0)],
        commands=commands,
        now_monotonic=21.0,
    )

    cast_action = commands.get_next()
    town_action = commands.get_next()

    assert cast_action is not None and cast_action.cast_spell == "curse"
    assert town_action is not None and town_action.cast_spell == "town_portal"
