"""Utility timing helpers."""

import time


class FPSLimiter:
    def __init__(self, fps: int = 30):
        """Initialize a new `FPSLimiter` instance.

        Parameters:
            fps: Parameter for fps used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        if fps <= 0:
            raise ValueError("fps must be greater than 0")
        self.delay = 1.0 / fps
        self.last_time = time.monotonic()

    def wait(self):
        """Wait.

        Parameters:
            None.

        Local Variables:
            elapsed: Local variable for elapsed used in this routine.
            now: Local variable for now used in this routine.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        now = time.monotonic()
        elapsed = now - self.last_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_time = time.monotonic()