# main.py

from vision import Vision
from controller import Controller
from state_manager import StateManager
from policy.rule_policy import RulePolicy
from command_module import CommandModule
from utils.timing import FPSLimiter
from config import DEBUG

def main():
    vision = Vision()
    controller = Controller()
    state_manager = StateManager()
    policy = RulePolicy()
    commands = CommandModule()
    limiter = FPSLimiter(fps=30)

    level_number = 1

    while True:
        frame = vision.grab_frame()
        game_state = vision.extract_game_state(frame, level_number)
        current_state = state_manager.update_state(game_state)

        action = commands.get_next()
        if not action:
            action = policy.decide(game_state)

        if action.click_target:
            controller.click(*action.click_target)
        if action.cast_spell:
            controller.cast_spell(action.cast_spell)
        if action.stop:
            controller.stop_all()

        if DEBUG:
            print(f"State: {current_state}, Teammates: {game_state.teammate_positions}, Player: {game_state.player_position}, Action: {action.click_target}")

        limiter.wait()

if __name__ == "__main__":
    main()