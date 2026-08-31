from core.game import Game

from juegos.tictactoe.tictactoe import (
    TicTacToeGameState,
    TicTacToeForwardModel,
    SetCellAction,
    print_board,
    read_human_move,
)


class TicTacToeGame(Game):

    def __init__(self):
        super().__init__("3 en raya")

    def create_state(self):
        return TicTacToeGameState()

    def create_model(self):
        return TicTacToeForwardModel()

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        x, y = move
        return SetCellAction(x, y, player_id)

    def print_board(self, state):
        print_board(state)

    def print_ai_action(self, action):
        print(f"IA juega: ({action.x}, {action.y})")