from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState

@dataclass
class TicTacToeGameState(GameState):
    """
    Estado del juego de 3 en raya.

    Atributos:
    - grid_size: tamaño del tablero (por defecto 3)
    - board: lista lineal con las celdas
             0 = vacía, 1 = jugador 1, 2 = jugador 2
    - current_player: jugador al que le toca mover
    - is_terminal: indica si la partida ha terminado
    - winner: 1, 2 o None si hay empate / no decidido aún
    """
    grid_size: int = 3
    board: Optional[list[int]] = None
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        """
        Si no se pasa un tablero, se crea vacío.
        """
        if self.board is None:
            self.board = [0] * (self.grid_size * self.grid_size)

    def clone(self):
        """
        Devuelve una copia profunda del estado.
        Muy importante para los algoritmos de búsqueda.
        """
        return TicTacToeGameState(
            grid_size=self.grid_size,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def get(self, x: int, y: int) -> int:
        """
        Devuelve el valor de la celda (x, y).
        """
        return self.board[y * self.grid_size + x]

    def set(self, x: int, y: int, value: int):
        """
        Asigna un valor a la celda (x, y).
        """
        self.board[y * self.grid_size + x] = value