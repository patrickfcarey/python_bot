# policy/ml_policy.py
from game_state import GameState, Action

class MLPolicy:
    def __init__(self, model):
        self.model = model  # load your trained ML model

    def decide(self, state: GameState) -> Action:
        # state → ML → Action
        return self.model.predict(state)