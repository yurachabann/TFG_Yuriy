from core.game import Game

from .game_state import CheckersGameState
from .forward_model import CheckersForwardModel
from .actions import MovePieceAction
from .console import print_board, read_human_move


class CheckersGame(Game):
    """
    Wrapper class that integrates Checkers into the framework.

    This class does NOT contain game logic.
    It only connects the game implementation with:
    - Match
    - Players
    - AI algorithms
    """

    def __init__(self):
        super().__init__("Damas")

    def create_state(self):
        """
        Create initial game state.
        """
        return CheckersGameState()

    def create_model(self):
        """
        Create forward model (rules engine).
        """
        return CheckersForwardModel()

    def read_human_move(self, state):
        """
        Read move from console for a human player.
        """
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        """
        Convert a move into a GameAction.
        """
        return MovePieceAction(
            path=move,
            player=player_id
        )

    def print_board(self, state):
        """
        Print board to console.
        """
        print_board(state)

    def print_ai_action(self, action):
        """
        Print AI move.
        """
        print("AI plays:", action.path)