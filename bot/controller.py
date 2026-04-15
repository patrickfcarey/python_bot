"""Controller abstractions for input actions."""

import pyautogui

from bot.config import MOVE_KEY, SPELL_KEYS, STOP_KEY


class Action:
    def __init__(self):
        self.click_target = None
        self.cast_spell = None
        self.stop = False


class Controller:
    def move_forward(self, on=True):
        if on:
            pyautogui.keyDown(MOVE_KEY)
        else:
            pyautogui.keyUp(MOVE_KEY)

    def stop_all(self):
        pyautogui.keyUp(MOVE_KEY)
        pyautogui.keyUp(STOP_KEY)

    def click(self, x, y):
        pyautogui.click(x, y)

    def cast_spell(self, slot):
        key = SPELL_KEYS.get(slot)
        if key:
            pyautogui.press(key)