"""Stub ML policy adapter."""

from bot.controller import Action
from bot.game_state import GameState


class MLPolicy:
    def __init__(self, model):
        self.model = model  # Load your trained ML model.

    def decide(self, state: GameState) -> Action:
        # state -> model -> Action
        return self.model.predict(state)