# config.py
from typing import Tuple

# Screen capture region (top-left corner)
AUTOMAP_REGION = {"top": 0, "left": 0, "width": 800, "height": 600}

# Loading detection threshold (brightness)
LOADING_BRIGHTNESS_THRESHOLD = 30

# Time to stabilize on new level
LEVEL_STABILIZE_TIME = 2.0  # seconds

# Turn/movement sensitivity
TURN_SENSITIVITY = 0.2

# Controller keys
MOVE_KEY = "w"
SPELL_KEYS = {"primary": "1"}

# Logging
DEBUG = True