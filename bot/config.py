"""Project-wide runtime configuration."""

# Screen capture region (top-left corner)
AUTOMAP_REGION = {"top": 0, "left": 0, "width": 800, "height": 600}

# Loading detection threshold (brightness)
LOADING_BRIGHTNESS_THRESHOLD = 30

# Time to stabilize after level changes
LEVEL_STABILIZE_TIME = 2.0  # seconds

# Turn/movement sensitivity
TURN_SENSITIVITY = 0.2

# Controller keys
MOVE_KEY = "w"
STOP_KEY = "s"
SPELL_KEYS = {"primary": "1"}

# Paths
TEMPLATE_PATH = "bot/templates/green_x.png"
SCREENSHOT_PATH = "bot/tests/screenshots"

# Logging
DEBUG = True