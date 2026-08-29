from __future__ import annotations
from typing import Any
from juegos.battleship.game_state import BattleshipGameState


class BattleshipPIMCHeuristic:
    """
    Heurística para evaluar estados determinizados de Battleship tras un disparo.
    Adecuada para PIMC con Alfa-Beta a profundidad 1.
    """

    def __init__(
        self,
        hit_weight: float = 100.0,
        sink_weight: float = 500.0,
        miss_penalty: float = -10.0
    ):
        self.hit_weight = hit_weight
        self.sink_weight = sink_weight
        self.miss_penalty = miss_penalty

    def evaluate(self, state: BattleshipGameState, ai_player: int) -> float:
        """
        Evalúa el estado desde la perspectiva de ai_player.
        """
        enemy_id = 2 if ai_player == 1 else 1

        # Todas las casillas ocupadas por barcos enemigos en esta determinización
        enemy_ship_cells = set().union(*state.ships[enemy_id]) if state.ships[enemy_id] else set()
        
        # Disparos realizados por la IA
        my_shots = state.shots[ai_player]

        # Impactos acertados
        hits = my_shots.intersection(enemy_ship_cells)
        # Fallos (agua)
        misses = my_shots - hits

        # Barcos completamente hundidos
        sunk_ships_count = sum(
            1 for ship in state.ships[enemy_id]
            if ship.issubset(my_shots)
        )

        score = (
            len(hits) * self.hit_weight
            + sunk_ships_count * self.sink_weight
            + len(misses) * self.miss_penalty
        )

        return score