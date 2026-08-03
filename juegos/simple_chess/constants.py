# ============================================================
# CONSTANTES DEL TABLERO Y DE LAS PIEZAS
# ============================================================

# Representación interna de una casilla vacía.
EMPTY = "."
# Identificador del jugador blanco.
WHITE = 1
# Identificador del jugador negro.
BLACK = 2
# Código interno del peón.
PAWN = "P"
# Código interno del caballo.
KNIGHT = "N"
# Código interno del alfil.
BISHOP = "B"
# Código interno de la torre.
ROOK = "R"
# Código interno de la dama.
QUEEN = "Q"
# Código interno del rey.
KING = "K"


# Símbolos Unicode usados para mostrar las piezas blancas en consola.
WHITE_PIECES = {
    PAWN: "♙",
    KNIGHT: "♘",
    BISHOP: "♗",
    ROOK: "♖",
    QUEEN: "♕",
    KING: "♔"
}


# Símbolos Unicode usados para mostrar las piezas negras en consola.
BLACK_PIECES = {
    PAWN: "♟",
    KNIGHT: "♞",
    BISHOP: "♝",
    ROOK: "♜",
    QUEEN: "♛",
    KING: "♚"
}

__all__ = [
    "EMPTY",
    "WHITE",
    "BLACK",
    "PAWN",
    "KNIGHT",
    "BISHOP",
    "ROOK",
    "QUEEN",
    "KING",
    "WHITE_PIECES",
    "BLACK_PIECES"
]