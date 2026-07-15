from generic.heuristic import Heuristic

from juegos.simple_chess.simple_chess import (
    SimpleChessGameState,
    SimpleChessForwardModel,
    EMPTY,
    PAWN,
    KNIGHT,
    BISHOP,
    ROOK,
    QUEEN,
    KING,
    piece_player,
    piece_type,
    other_player
)


class SimpleChessHeuristic(Heuristic[SimpleChessGameState]):
    """Valora material, movilidad y control del centro."""

    PIECE_VALUES = {
        PAWN: 100,
        KNIGHT: 320,
        BISHOP: 330,
        ROOK: 500,
        QUEEN: 900,
        KING: 20000
    }

    MOBILITY_WEIGHT = 5
    CENTER_WEIGHT = 20
    CENTER_SQUARES = {(3, 3), (4, 3), (3, 4), (4, 4)}

    def evaluate(self, state: SimpleChessGameState, ai_player: int) -> float:
        opponent = other_player(ai_player)
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

        model = SimpleChessForwardModel()

        ai_state = state.clone()
        ai_state.current_player = ai_player
        ai_moves = len(model.compute_available_actions(ai_state))

        opponent_state = state.clone()
        opponent_state.current_player = opponent
        opponent_moves = len(model.compute_available_actions(opponent_state))

        score += (ai_moves - opponent_moves) * self.MOBILITY_WEIGHT
        return float(score)
