from .constants import EMPTY, PLAYER_1, PLAYER_2
from .game_state import TicTacToeGameState


def print_board(state: TicTacToeGameState):

    symbols = {
        EMPTY: ".",
        PLAYER_1: "X",
        PLAYER_2: "O"
    }

    g = state.grid_size

    print()
    print("    ", end="")

    for x in range(g):
        print(f"{x} ", end="")

    print()

    for y in range(g):
        print(f"{y} | ", end="")

        for x in range(g):
            print(symbols[state.get(x, y)], end=" ")

        print()

    print()


def read_human_move(state: TicTacToeGameState):

    while True:

        try:
            print("Introduce movimiento como: x y")
            x, y = map(int, input("Movimiento: ").split())
        except ValueError:
            print("Formato inválido")
            continue

        g = state.grid_size

        if not (0 <= x < g and 0 <= y < g):
            print("Movimiento fuera de rango")
            continue

        if state.get(x, y) != EMPTY:
            print("La celda está ocupada")
            continue

        return x, y