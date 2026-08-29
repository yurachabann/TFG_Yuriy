from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState
from .constants import EMPTY, WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN
from .helpers import make_piece

@dataclass
class SimpleChessGameState(GameState):
    """Estado del ajedrez simplificado."""

    board: Optional[list[str]] = None
    current_player: int = WHITE
    is_terminal: bool = False
    winner: Optional[int] = None
    moves_without_progress: int = 0


    # __post_init__ se ejecuta justo después del constructor generado
    # por dataclass y prepara el tablero cuando no se proporcionó uno.
    def __post_init__(self):
        if self.board is None:
            self.board = self.create_initial_board()


    # Crea un tablero de 64 casillas con la disposición inicial estándar.
    def create_initial_board(self) -> list[str]:
        board = [EMPTY] * 64

        back_rank = [
            ROOK,
            KNIGHT,
            BISHOP,
            QUEEN,
            KING,
            BISHOP,
            KNIGHT,
            ROOK
        ]

        for x, kind in enumerate(back_rank):
            board[self.index(x, 0)] = make_piece(BLACK, kind)
            board[self.index(x, 7)] = make_piece(WHITE, kind)

        for x in range(8):
            board[self.index(x, 1)] = make_piece(BLACK, PAWN)
            board[self.index(x, 6)] = make_piece(WHITE, PAWN)

        return board


    # Crea una copia independiente del estado.
    # Los algoritmos de búsqueda usan clones para simular jugadas.
    def clone(self):
        return SimpleChessGameState(
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner,
            moves_without_progress=self.moves_without_progress
        )


    # Convierte coordenadas bidimensionales en un índice de lista.
    def index(self, x: int, y: int) -> int:
        return y * 8 + x


    # Lee el contenido de una casilla.
    def get(self, x: int, y: int) -> str:
        return self.board[self.index(x, y)]


    # Sustituye el contenido de una casilla.
    def set(self, x: int, y: int, value: str):
        self.board[self.index(x, y)] = value


    # Comprueba que las coordenadas pertenezcan al tablero 8x8.
    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < 8 and 0 <= y < 8