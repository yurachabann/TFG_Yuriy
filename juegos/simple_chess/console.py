from .helpers import player_label, piece_symbol
from .forward_model import SimpleChessForwardModel
from .game_state import SimpleChessGameState
from .actions import MovePieceAction


# Muestra el tablero y el estado del turno en formato legible.
def print_board(state: SimpleChessGameState):
    print()
    print("=== AJEDREZ SIMPLIFICADO ===")
    print(
        "Jugador actual:",
        player_label(state.current_player)
    )
    print()
    print("Jugador 1 (Humano): Blancas ♙")
    print("Jugador 2 (IA): Negras ♟")

    # Se informa cuando el jugador actual debe responder a un jaque.
    model = SimpleChessForwardModel()

    if model.is_king_attacked(
        state,
        state.current_player
    ):
        print(
            "JAQUE:",
            player_label(state.current_player),
            "debe proteger su rey."
        )

    print()
    print("    a  b  c  d  e  f  g  h")

    for y in range(8):
        rank = 8 - y
        print(f"{rank} |", end=" ")

        for x in range(8):
            print(
                piece_symbol(state.get(x, y)),
                end="  "
            )

        print(f"| {rank}")

    print("    a  b  c  d  e  f  g  h")
    print()



# Convierte una casilla escrita por el usuario, como 'e2',
# en coordenadas internas (x, y).
def parse_square(square: str) -> tuple[int, int]:
    square = square.strip().lower()

    if (
        len(square) != 2
        or square[0] not in "abcdefgh"
        or square[1] not in "12345678"
    ):
        raise ValueError("Casilla inválida.")

    return (
        ord(square[0]) - ord("a"),
        8 - int(square[1])
    )



# Convierte coordenadas internas en notación de casilla, como 'e2'.
def square_name(x: int, y: int) -> str:
    return f"{chr(ord('a') + x)}{8 - y}"



# Lee movimientos del usuario hasta recibir uno con formato y reglas válidas.
def read_human_move(state: SimpleChessGameState):
    # El mismo forward model que usa la IA se reutiliza para validar
    # los movimientos escritos por el jugador humano.
    model = SimpleChessForwardModel()
    actions = model.compute_available_actions(state)

    while True:
        try:
            origin, destination = input(
                "Movimiento del Jugador 1 "
                "(Humano - Blancas), ejemplo e2 e4: "
            ).split()

            from_x, from_y = parse_square(origin)
            to_x, to_y = parse_square(destination)

        except ValueError:
            print(
                "Formato inválido. "
                "Ejemplo correcto: e2 e4"
            )
            continue

        action = MovePieceAction(
            from_x,
            from_y,
            to_x,
            to_y,
            state.current_player
        )

        if action not in actions:
            print("Movimiento no permitido.")
            continue

        return from_x, from_y, to_x, to_y