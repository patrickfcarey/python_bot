bot/
|-- __init__.py
|-- main.py
|-- config.py
|-- controller.py
|-- command_module.py
|-- game_state.py
|-- state_manager.py
|-- vision.py
|-- enemy_tracker.py
|-- combat.py
|-- performance.py
|-- window_manager.py
|-- ocr_dataset.py
|-- runtime_checks.py
|-- policy/
|   |-- __init__.py
|   |-- rule_policy.py
|   `-- ml_policy.py
|-- utils/
|   `-- timing.py
|-- templates/
|   `-- README.txt
`-- tests/
    |-- test_combat.py
    |-- test_command_module.py
    |-- test_controller.py
    |-- test_enemy_tracker.py
    |-- test_performance.py
    |-- test_rule_policy.py
    |-- test_state_manager.py
    `-- test_window_manager.py

scripts/
`-- augment_ocr_dataset.py

data/
`-- ocr/
    |-- raw/
    `-- labeled/

logs/
`-- bot.log (created at runtime)