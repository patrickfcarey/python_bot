# utils/timing.py

import time

class FPSLimiter:
    def __init__(self, fps=30):
        self.delay = 1.0 / fps
        self.last_time = time.time()

    def wait(self):
        elapsed = time.time() - self.last_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_time = time.time()