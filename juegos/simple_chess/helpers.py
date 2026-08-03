from .constants import WHITE, BLACK, EMPTY, WHITE_PIECES, BLACK_PIECES
from typing import Optional

# Devuelve el identificador del jugador contrario.
def other_player(player: int) -> int:
    return WHITE if player == BLACK else BLACK


def player_label(player: int) -> str:
    """
    Devuelve el nombre visible del jugador.

    En el modo Humano vs IA:
    - el jugador 1 controla las piezas blancas
    - el jugador 2 controla las piezas negras
    """
    if player == WHITE:
        return "Jugador 1 (Humano - Blancas)"

    return "Jugador 2 (IA - Negras)"



# Construye la representación interna de una pieza.
# Ejemplos: 'wP' = peón blanco, 'bK' = rey negro.
def make_piece(player: int, kind: str) -> str:
    return ("w" if player == WHITE else "b") + kind



# Obtiene el propietario de una pieza a partir de su prefijo.
def piece_player(piece: str) -> Optional[int]:
    if piece == EMPTY:
        return None

    return WHITE if piece[0] == "w" else BLACK



# Obtiene el tipo de pieza a partir de su segundo carácter.
def piece_type(piece: str) -> Optional[str]:
    return None if piece == EMPTY else piece[1]



# Convierte la representación interna en el símbolo Unicode visible.
def piece_symbol(piece: str) -> str:
    if piece == EMPTY:
        return EMPTY

    symbols = (
        WHITE_PIECES
        if piece_player(piece) == WHITE
        else BLACK_PIECES
    )

    return symbols[piece_type(piece)]

# Convierte coordenadas internas en notación de casilla, como 'e2'.
def square_name(x: int, y: int) -> str:
    return f"{chr(ord('a') + x)}{8 - y}"
