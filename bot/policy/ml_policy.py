"""Stub ML policy adapter."""

from bot.controller import Action
from bot.game_state import GameState


class MLPolicy:
    def __init__(self, model):
        """Initialize a new `MLPolicy` instance.

        Parameters:
            model: Parameter for model used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.model = model

    def decide(self, state: GameState) -> Action:
        """Decide.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Action`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return self.model.predict(state)