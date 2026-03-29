# game_state.py
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class GameState:
    automap_matrix: Optional[any]
    teammate_positions: List[Tuple[int, int]]   # absolute positions on automap
    player_position: Tuple[int, int]            # absolute position on automap
    relative_vectors: List[Tuple[float, float]] = None  # player -> teammates
    level_number: int = 0
    loading: bool = False