from generic.heuristic import Heuristic

from juegos.simple_chess.game_state import SimpleChessGameState
from juegos.simple_chess.constants import EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from juegos.simple_chess.helpers import piece_player, piece_type

class SimpleChessHeuristic(Heuristic[SimpleChessGameState]):
    """Valora material y control del centro."""

    PIECE_VALUES = {
        PAWN: 100,
        KNIGHT: 320,
        BISHOP: 330,
        ROOK: 500,
        QUEEN: 900,
        KING: 20000
    }

    CENTER_WEIGHT = 20
    CENTER_SQUARES = {(3, 3), (4, 3), (3, 4), (4, 4)}

    def evaluate(self, state: SimpleChessGameState, ai_player: int) -> float:
        score = 0.0

        for y in range(8):
            for x in range(8):
                piece = state.get(x, y)
                if piece == EMPTY:
                    continue

                value = self.PIECE_VALUES[piece_type(piece)]
                owner = piece_player(piece)

                if owner == ai_player:
                    score += value
                    if (x, y) in self.CENTER_SQUARES:
                        score += self.CENTER_WEIGHT
                else:
                    score -= value
                    if (x, y) in self.CENTER_SQUARES:
                        score -= self.CENTER_WEIGHT

        return float(score)