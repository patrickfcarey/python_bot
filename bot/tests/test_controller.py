# tests/test_controller.py
from unittest.mock import patch
from controller import Controller

def test_move_forward():
    controller = Controller()
    with patch("pyautogui.keyDown") as kd, patch("pyautogui.keyUp") as ku:
        controller.move_forward(True)
        kd.assert_called_once()
        controller.move_forward(False)
        ku.assert_called_once()