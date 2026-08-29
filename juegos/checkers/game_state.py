from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState

from .constants import (
    EMPTY,
    P1_MAN,
    P2_MAN,
)

@dataclass
class CheckersGameState(GameState):

    size: int = 8
    board: Optional[list[int]] = None
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None
    moves_without_progress: int = 0

    def __post_init__(self):
        """
        Este método se ejecuta automáticamente después de crear el dataclass.

        Si no se ha pasado un tablero concreto, se crea un tablero vacío
        y se colocan las piezas iniciales.
        """
        if self.board is None:
            self.board = [EMPTY] * (self.size * self.size)
            self.setup_initial_board()

    def setup_initial_board(self) -> None:
        """
        Coloca las piezas iniciales.

        Queremos que jugador 1, que es x, aparezca abajo.

        Por tanto:
        - jugador 2 empieza arriba: filas 0, 1, 2.
        - jugador 1 empieza abajo: filas 5, 6, 7.

        Solo se colocan piezas en casillas oscuras.
        En este tablero consideramos casilla oscura si:
            (x + y) % 2 == 1
        """
        # Jugador 2 arriba.
        for y in range(3):
            for x in range(self.size):
                if self.is_dark_square(x, y):
                    self.set(x, y, P2_MAN)

        # Jugador 1 abajo.
        for y in range(5, 8):
            for x in range(self.size):
                if self.is_dark_square(x, y):
                    self.set(x, y, P1_MAN)

    def clone(self) -> "CheckersGameState":
        """
        Devuelve una copia independiente del estado.

        Esto es imprescindible para algoritmos como:
        - Minimax
        - Alpha-Beta
        - MCTS

        Porque esos algoritmos simulan jugadas sin modificar el estado real.
        """
        return CheckersGameState(
            size=self.size,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner,
            moves_without_progress=self.moves_without_progress
        )

    def index(self, x: int, y: int) -> int:
        """
        Convierte coordenadas 2D en índice de lista.

        Ejemplo:
        - tablero 8x8
        - posición (3, 2)
        - índice = 2 * 8 + 3 = 19
        """
        return y * self.size + x

    def inside(self, x: int, y: int) -> bool:
        """
        Comprueba si una coordenada está dentro del tablero.
        """
        return 0 <= x < self.size and 0 <= y < self.size

    def is_dark_square(self, x: int, y: int) -> bool:
        """
        En damas solo se juega en las casillas oscuras.

        Con esta fórmula alternamos las casillas.
        """
        return (x + y) % 2 == 1

    def get(self, x: int, y: int) -> int:
        """
        Devuelve la pieza que hay en una casilla.
        """
        return self.board[self.index(x, y)]

    def set(self, x: int, y: int, value: int) -> None:
        """
        Escribe una pieza en una casilla.
        """
        self.board[self.index(x, y)] = value