from juegos.tictactoe.tictactoe import (
    TicTacToeGameState,
    TicTacToeForwardModel,
    SetCellAction,
    print_board,
    read_human_move,
)


def create_state():
    return TicTacToeGameState()


def create_model():
    return TicTacToeForwardModel()


def apply_human_move(state, move, player):
    x, y = move
    action = SetCellAction(x, y, player)
    create_model().advance(state, action)


def print_ai_action(action):
    print("IA juega:", action.x, action.y)


GAME = {
    "name": "3 en raya",
    "create_state": create_state,
    "create_model": create_model,
    "print_board": print_board,
    "read_human_move": read_human_move,
    "apply_human_move": apply_human_move,
    "print_ai_action": print_ai_action,
}