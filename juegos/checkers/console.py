from __future__ import annotations

from .game_state import CheckersGameState
from .actions import MovePieceAction
from .forward_model import CheckersForwardModel
from .constants import (
    EMPTY,
    P1_MAN,
    P2_MAN,
    P1_KING,
    P2_KING,
)

def print_board(state: CheckersGameState) -> None:
    """
    Imprime el tablero por consola.

    Como jugador 1 = x empieza abajo, imprimimos y de 0 a 7,
    que es la forma normal de representar una matriz:
    - fila 0 arriba
    - fila 7 abajo

    Así se ve:
    - o arriba
    - x abajo
    """
    symbols = {
        EMPTY: ".",
        P1_MAN: "x",
        P2_MAN: "o",
        P1_KING: "X",
        P2_KING: "O",
    }

    print()
    print("    ", end="")
    for x in range(state.size):
        print(f"{x} ", end="")
    print()

    for y in range(state.size):
        print(f"{y} | ", end="")

        for x in range(state.size):
            print(symbols[state.get(x, y)], end=" ")

        print()

    print()
    print("x = jugador 1, o = jugador 2, X/O = dama")
    print(f"Turno actual: jugador {state.current_player}")
    print()


def read_human_move(state: CheckersGameState) -> list[tuple[int, int]]:

    model = CheckersForwardModel()

    while True:
        legal_actions = model.compute_available_actions(state)

        print("Introduce movimiento como: x1 y1 x2 y2")
        print("Para captura múltiple: x1 y1 x2 y2 x3 y3 ...")

        if state.current_player == 1:
            print("Te toca mover: x / X")
        else:
            print("Te toca mover: o / O")

        try:
            values = list(map(int, input("Movimiento: ").split()))
        except ValueError:
            print("Formato inválido. Usa solo números.")
            continue

        if len(values) < 4 or len(values) % 2 != 0:
            print("Debes introducir pares de coordenadas.")
            continue

        path: list[tuple[int, int]] = []
        valid_coordinates = True

        for i in range(0, len(values), 2):
            x = values[i]
            y = values[i + 1]

            if not state.inside(x, y):
                print("Coordenada fuera de rango.")
                valid_coordinates = False
                break

            path.append((x, y))

        if not valid_coordinates:
            continue

        action = MovePieceAction(
            path=path,
            player=state.current_player
        )

        if action in legal_actions:
            return path

        print("Movimiento ilegal.")
        print("Movimientos legales disponibles:")

        for legal_action in legal_actions:
            print(" -", legal_action.path)

        print()