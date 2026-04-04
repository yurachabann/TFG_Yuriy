from juegos.four_in_line.four_in_line import (
    ConnectFourGameState,
    ConnectFourForwardModel,
    DropPieceAction,
    print_board,
    read_human_move,
)


def create_state():
    return ConnectFourGameState(width=7, height=6)


def create_model():
    return ConnectFourForwardModel()


def apply_human_move(state, move, player):
    action = DropPieceAction(move, player)
    create_model().advance(state, action)


def print_ai_action(action):
    print("IA juega columna:", action.column)


GAME = {
    "name": "4 en raya",
    "create_state": create_state,
    "create_model": create_model,
    "print_board": print_board,
    "read_human_move": read_human_move,
    "apply_human_move": apply_human_move,
    "print_ai_action": print_ai_action,
}