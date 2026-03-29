bot/
├── main.py                # Entry point
├── config.py              # All configurable constants
├── controller.py          # Handles mouse/keyboard input
├── vision.py              # Captures screen + interprets automap
├── state_manager.py       # Tracks loading, new level, playing
├── game_state.py          # Data models for ML-ready structured state
├── policy/                # Decision layer (rule-based now, ML later)
│   ├── __init__.py
│   ├── rule_policy.py
│   └── ml_policy.py
├── command_module.py      # Command queue + overrides
└── utils/
    └── timing.py          # Utility functions (FPS, sleep, etc.)