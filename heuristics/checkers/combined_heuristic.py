# heuristics/checkers/combined_heuristic.py

"""
        Heurística para estados no terminales.

        Sirve para:
        - minimax con profundidad máxima
        - alpha-beta con profundidad máxima
        - MCTS con max_rollout_depth si se corta el rollout

        La heurística valora:
        - cantidad de piezas
        - damas valen más que peones
        - avance de peones hacia la coronación

        Como jugador 1 empieza abajo y avanza hacia arriba:
        - P1_MAN está más avanzado cuanto menor es y.
        - P2_MAN está más avanzado cuanto mayor es y.
        """

from generic.heuristic import Heuristic
from juegos.checkers.constants import (
    EMPTY,
    P1_MAN,
    P2_MAN,
)

from juegos.checkers.helpers import (
    owner_of,
    other_player,
)

from juegos.checkers.game_state import CheckersGameState;

class CheckersCombinedHeuristic(Heuristic[CheckersGameState]):

    def evaluate(
        self,
        state: CheckersGameState,
        ai_player: int
    ) -> float:
        opponent = other_player(ai_player)
        score = 0

        for y in range(state.size):
            for x in range(state.size):
                piece = state.get(x, y)

                if piece == EMPTY:
                    continue

                piece_owner = owner_of(piece)

                if piece in (P1_MAN, P2_MAN):
                    value = 100
                else:
                    value = 175

                if piece == P1_MAN:
                    value += (state.size - 1 - y) * 5
                elif piece == P2_MAN:
                    value += y * 5

                if piece_owner == ai_player:
                    score += value
                elif piece_owner == opponent:
                    score -= value

        return score