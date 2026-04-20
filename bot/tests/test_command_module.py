"""Tests for command queue behavior."""

from bot.command_module import CommandModule
from bot.controller import Action


def test_command_queue_fifo():
    queue = CommandModule()
    first = Action(reason="first")
    second = Action(reason="second")

    queue.add_command(first)
    queue.add_command(second)

    assert queue.size() == 2
    assert queue.get_next().reason == "first"
    assert queue.get_next().reason == "second"
    assert queue.get_next() is None


def test_command_module_pause_and_runtime_overrides():
    commands = CommandModule()

    assert commands.is_paused() is False
    assert commands.is_combat_enabled(default_enabled=True) is True
    assert commands.is_pickup_enabled(default_enabled=False) is False
    assert commands.is_potion_enabled(default_enabled=True) is True

    commands.set_paused(True)
    commands.set_combat_enabled_override(False)
    commands.set_pickup_enabled_override(True)
    commands.set_potion_enabled_override(False)

    assert commands.is_paused() is True
    assert commands.is_combat_enabled(default_enabled=True) is False
    assert commands.is_pickup_enabled(default_enabled=False) is True
    assert commands.is_potion_enabled(default_enabled=True) is False

    commands.reset_overrides()

    assert commands.is_paused() is False
    assert commands.is_combat_enabled(default_enabled=True) is True
    assert commands.is_pickup_enabled(default_enabled=False) is False
    assert commands.is_potion_enabled(default_enabled=True) is True

def test_command_module_clear_pending_commands_returns_removed_count():
    commands = CommandModule()
    commands.add_command(Action(reason="one"))
    commands.add_command(Action(reason="two"))

    removed = commands.clear_pending_commands()

    assert removed == 2
    assert commands.size() == 0
    assert commands.get_next() is None
