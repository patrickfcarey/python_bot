bot/
|-- __init__.py                 # Package marker
|-- main.py                     # Entry point (run with python -m bot.main)
|-- config.py                   # Configurable constants
|-- controller.py               # Mouse/keyboard execution
|-- vision.py                   # Screen capture + automap interpretation
|-- state_manager.py            # Lifecycle state transitions
|-- game_state.py               # Structured state model
|-- command_module.py           # Override command queue
|-- policy/
|   |-- __init__.py
|   |-- rule_policy.py          # Rule-based baseline policy
|   `-- ml_policy.py            # ML policy adapter stub
|-- utils/
|   `-- timing.py               # FPS limiter
|-- templates/
|   `-- README.txt              # Placeholder for template assets
`-- tests/
    |-- test_controller.py
    |-- test_rule_policy.py
    |-- test_state_manager.py
    `-- screenshots/
        `-- README.txt          # Place vision test screenshots here