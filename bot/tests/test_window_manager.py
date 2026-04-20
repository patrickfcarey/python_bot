"""Tests for window-region math that do not require live OS window control."""

from dataclasses import replace

from bot.config import default_config
from bot.window_manager import GameWindowManager, WindowRect


def test_automap_region_respects_window_bounds():
    config = replace(
        default_config(),
        automap_offset_x=100,
        automap_offset_y=50,
        automap_width=1200,
        automap_height=700,
    )
    manager = GameWindowManager(config)

    window = WindowRect(left=10, top=20, width=900, height=600, title="Diablo II", source="test")
    region = manager.build_automap_region(window)

    assert region["left"] == 110
    assert region["top"] == 70
    assert region["width"] == 900
    assert region["height"] == 600