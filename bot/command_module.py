"""Simple FIFO command override queue."""

from bot.controller import Action


class CommandModule:
    def __init__(self):
        self.queue = []

    def add_command(self, cmd: Action):
        self.queue.append(cmd)

    def get_next(self):
        if self.queue:
            return self.queue.pop(0)
        return None