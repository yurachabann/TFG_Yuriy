from .game_state import ConnectFourGameState


def print_board(state: ConnectFourGameState) -> None:
    symbols = {
        0: ".",
        1: "X",
        2: "O",
    }

    print()

    for y in range(state.height):
        row = [
            symbols[state.get(x, y)]
            for x in range(state.width)
        ]
        print(f"{y} | " + " ".join(row))

    print("    " + " ".join(
        str(i) for i in range(state.width)
    ))

    print()


def read_human_move(state: ConnectFourGameState) -> int:

    while True:

        try:
            print("Introduce movimiento como: columna")
            col = int(input("Movimiento: ").strip())
        except ValueError:
            print("Formato inválido.")
            continue

        if not (0 <= col < state.width):
            print("Columna fuera de rango.")
            continue

        if state.get(col, 0) != 0:
            print("La columna está llena.")
            continue

        return col