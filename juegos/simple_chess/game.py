from core.game import Game

from .game_state import SimpleChessGameState
from .forward_model import SimpleChessForwardModel
from .actions import MovePieceAction
from .console import print_board, read_human_move
from .helpers import square_name

class SimpleChessGame(Game):
    """Integra el ajedrez simplificado con el framework."""

    def __init__(self):
        super().__init__("Ajedrez simplificado")

    def create_state(self):
        return SimpleChessGameState()

    def create_model(self):
        return SimpleChessForwardModel()

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        from_x, from_y, to_x, to_y = move
        return MovePieceAction(from_x, from_y, to_x, to_y, player_id)

    def print_board(self, state):
        print_board(state)

    def print_ai_action(self, action):
        print(
            "IA mueve:",
            square_name(action.from_x, action.from_y),
            "->",
            square_name(action.to_x, action.to_y)
        )
