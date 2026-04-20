"""Tests for controller action execution."""

from dataclasses import replace

from bot.config import default_config
from bot.controller import Action, Controller


class FakeBackend:
    def __init__(self):
        self.calls = []

    def keyDown(self, key):
        self.calls.append(("keyDown", key))

    def keyUp(self, key):
        self.calls.append(("keyUp", key))

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def press(self, key):
        self.calls.append(("press", key))


def test_execute_action_click_and_spell_and_move():
    config = replace(default_config(), dry_run=False)
    controller = Controller(config)
    backend = FakeBackend()
    controller._backend = backend

    action = Action(click_target=(100, 200), cast_spell="primary", hold_move=True)
    controller.execute_action(action)

    assert ("keyDown", config.move_key) in backend.calls
    assert ("press", config.spell_keys["primary"]) in backend.calls
    assert ("click", 100, 200) in backend.calls


def test_execute_action_stop():
    config = replace(default_config(), dry_run=False)
    controller = Controller(config)
    backend = FakeBackend()
    controller._backend = backend

    controller.execute_action(Action(stop=True))

    assert ("keyUp", config.move_key) in backend.calls
    assert ("keyUp", config.stop_key) in backend.calls