from core.game import Game

from juegos.tictactoe.tictactoe import (
    TicTacToeGameState,
    TicTacToeForwardModel,
    SetCellAction,
    print_board,
    read_human_move,
)


class TicTacToeGame(Game):
    """
    Wrapper class that integrates Tic Tac Toe into the framework.

    This class does NOT contain game logic.
    It only connects your existing implementation with:
    - Match
    - Players
    - AI algorithms
    """

    def __init__(self):
        super().__init__("3 en raya")

    def create_state(self):
        """
        Create initial game state.
        """
        return TicTacToeGameState()

    def create_model(self):
        """
        Create forward model (rules engine).
        """
        return TicTacToeForwardModel()

    def read_human_move(self, state):
        """
        Read move from console for a human player.
        """
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        """
        Convert (x, y) input into a GameAction.
        """
        x, y = move
        return SetCellAction(x, y, player_id)

    def print_board(self, state):
        """
        Print board to console.
        """
        print_board(state)

    def print_ai_action(self, action):
        """
        Print AI move.
        """
        print(f"AI plays: ({action.x}, {action.y})")