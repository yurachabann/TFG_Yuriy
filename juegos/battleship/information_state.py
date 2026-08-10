# En juegos/battleship/information_state.py

from dataclasses import dataclass, field
from typing import Set, Tuple, List


@dataclass
class BattleshipInformationState:
    observer_id: int
    grid_size: int
    my_ships: List[Set[Tuple[int, int]]]
    my_shots: Set[Tuple[int, int]]
    enemy_shots: Set[Tuple[int, int]]
    current_player: int
    my_hits: Set[Tuple[int, int]] = field(default_factory=set)
    sunk_ships: List[Set[Tuple[int, int]]] = field(default_factory=list)