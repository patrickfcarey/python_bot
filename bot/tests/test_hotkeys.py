"""Tests for Ctrl+Space pause hotkey monitor behavior."""

from bot.hotkeys import PauseHotkeyMonitor, VK_CONTROL, VK_SPACE


def test_pause_hotkey_monitor_toggles_once_per_combo_press_edge():
    state = {VK_CONTROL: False, VK_SPACE: False}

    monitor = PauseHotkeyMonitor(
        enabled=True,
        debounce_seconds=0.0,
        key_reader=lambda key: bool(state.get(key, False)),
    )

    assert monitor.poll(now_monotonic=1.0) is False

    state[VK_CONTROL] = True
    state[VK_SPACE] = True
    assert monitor.poll(now_monotonic=1.1) is True
    assert monitor.poll(now_monotonic=1.2) is False

    state[VK_SPACE] = False
    assert monitor.poll(now_monotonic=1.3) is False

    state[VK_SPACE] = True
    assert monitor.poll(now_monotonic=1.4) is True


def test_pause_hotkey_monitor_respects_debounce_window():
    state = {VK_CONTROL: True, VK_SPACE: True}

    monitor = PauseHotkeyMonitor(
        enabled=True,
        debounce_seconds=0.5,
        key_reader=lambda key: bool(state.get(key, False)),
    )

    assert monitor.poll(now_monotonic=2.0) is True
    assert monitor.poll(now_monotonic=2.1) is False

    state[VK_SPACE] = False
    assert monitor.poll(now_monotonic=2.2) is False

    state[VK_SPACE] = True
    assert monitor.poll(now_monotonic=2.3) is False
    assert monitor.poll(now_monotonic=2.7) is False

    state[VK_SPACE] = False
    monitor.poll(now_monotonic=2.8)
    state[VK_SPACE] = True
    assert monitor.poll(now_monotonic=2.9) is True


def test_pause_hotkey_monitor_returns_false_when_disabled():
    monitor = PauseHotkeyMonitor(enabled=False)

    assert monitor.poll(now_monotonic=1.0) is False
