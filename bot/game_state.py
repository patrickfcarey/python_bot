"""Game state data model."""

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass
class GameState:
    automap_matrix: Optional[Any]
    teammate_positions: List[Tuple[int, int]]
    player_position: Tuple[int, int]
    relative_vectors: Optional[List[Tuple[float, float]]] = None
    level_number: int = 0
    loading: bool = False
    last_action: Optional[str] = None