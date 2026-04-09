from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState
from generic.game_action import GameAction
from generic.forward_model import ForwardModel


# ============================================================
# GAME STATE
# ============================================================

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


# ============================================================
# ACTION
# ============================================================

@dataclass
class SetCellAction(GameAction):
    """
    Acción del juego:
    colocar la ficha de 'player' en la posición (x, y).
    """
    x: int
    y: int
    player: int


# ============================================================
# FORWARD MODEL
# ============================================================

class TicTacToeForwardModel(ForwardModel[TicTacToeGameState, SetCellAction]):
    """
    Forward model de 3 en raya.

    Se encarga de:
    - generar acciones legales
    - avanzar el estado
    - evaluar terminales
    """

    def compute_available_actions(self, state: TicTacToeGameState) -> list[SetCellAction]:
        """
        Devuelve todas las acciones legales posibles desde el estado actual.
        """
        if state.is_terminal:
            return []

        actions = []

        for y in range(state.grid_size):
            for x in range(state.grid_size):
                if state.get(x, y) == 0:
                    actions.append(SetCellAction(x, y, state.current_player))

        return actions

    def advance(self, state: TicTacToeGameState, action: SetCellAction) -> None:
        """
        Aplica una acción al estado.

        Reglas:
        - si el estado ya es terminal, no hace nada
        - coloca la ficha
        - comprueba victoria
        - comprueba empate
        - cambia de jugador si la partida continúa
        """
        if state.is_terminal:
            return

        # Validación mínima: no permitir jugar sobre una casilla ocupada
        if state.get(action.x, action.y) != 0:
            raise ValueError(f"La celda ({action.x}, {action.y}) ya está ocupada.")

        # Validación mínima: que el jugador de la acción coincida con el turno
        if action.player != state.current_player:
            raise ValueError(
                f"Turno inválido: action.player={action.player}, "
                f"pero current_player={state.current_player}."
            )

        state.set(action.x, action.y, action.player)

        if self.check_win(state, action.player):
            state.is_terminal = True
            state.winner = action.player
            return

        if all(cell != 0 for cell in state.board):
            state.is_terminal = True
            state.winner = None
            return

        state.current_player = 1 if state.current_player == 2 else 2

    def evaluate_terminal(self, state: TicTacToeGameState, ai_player: int, depth: int) -> int:
        """
        Evalúa un estado terminal para minimax.

        Convención:
        - victoria IA: positiva
        - derrota IA: negativa
        - empate: 0

        Se usa la profundidad para preferir:
        - ganar antes
        - perder más tarde
        """
        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 10 - depth

        return -10 + depth

    def check_win(self, state: TicTacToeGameState, player: int) -> bool:
        """
        Comprueba si 'player' ha ganado.
        """
        g = state.grid_size

        # Filas
        for y in range(g):
            if all(state.get(x, y) == player for x in range(g)):
                return True

        # Columnas
        for x in range(g):
            if all(state.get(x, y) == player for y in range(g)):
                return True

        # Diagonal principal
        if all(state.get(i, i) == player for i in range(g)):
            return True

        # Diagonal secundaria
        if all(state.get(g - 1 - i, i) == player for i in range(g)):
            return True

        return False


# ============================================================
# CONSOLE HELPERS
# ============================================================

def print_board(state: TicTacToeGameState):
    """
    Muestra el tablero por consola.
    """
    symbols = {0: ".", 1: "X", 2: "O"}
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
    """
    Lee por consola una jugada humana válida y devuelve (x, y).
    """
    while True:
        try:
            print("Introduce movimiento como: x y  (ejemplo: 1 2)")
            x, y = map(int, input("Movimiento (x y): ").split())
        except ValueError:
            print("Formato inválido. Ejemplo correcto: 1 2")
            continue

        g = state.grid_size

        if not (0 <= x < g and 0 <= y < g):
            print("Movimiento fuera de rango")
            continue

        if state.get(x, y) != 0:
            print("La celda está ocupada")
            continue

        return x, y