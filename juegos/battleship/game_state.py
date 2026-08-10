from dataclasses import dataclass, field
from typing import Optional, Set, Tuple
from generic.imperfect.game_state import ImperfectGameState

# Tamaños estándar de barcos en Hundir la Flota
SHIP_SIZES = [5, 4, 3, 3, 2]

@dataclass
class BattleshipGameState(ImperfectGameState):
    grid_size: int = 10
    num_players: int = 2
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None
    
    # ships[p] = Lista de conjuntos de coordenadas (r, c) de cada barco del jugador p
    ships: dict[int, list[Set[Tuple[int, int]]]] = field(default_factory=dict)
    
    # shots[p] = Conjunto de coordenadas (r, c) donde el jugador p ha disparado
    shots: dict[int, Set[Tuple[int, int]]] = field(default_factory=dict)
    
    last_action_summary: Optional[str] = None

    def __post_init__(self):
        if not self.ships:
            self.ships = {i: [] for i in range(1, self.num_players + 1)}
            self.shots = {i: set() for i in range(1, self.num_players + 1)}

    def clone(self):
        new_state = BattleshipGameState(
            grid_size=self.grid_size,
            num_players=self.num_players,
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner,
            last_action_summary=self.last_action_summary,
            shots={p: s.copy() for p, s in self.shots.items()}
        )
        new_state.ships = {p: [s.copy() for s in ship_list] for p, ship_list in self.ships.items()}
        return new_state