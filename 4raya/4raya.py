from dataclasses import dataclass
from typing import List, Optional
import random

# ============================================================
# 1. Estado del juego (4 en raya)
# ============================================================

@dataclass
class ConnectFourGameState:
    width: int = 7   # columnas
    height: int = 6  # filas
    board: List[int] = None  # 0 = vacío, 1 = jugador1, 2 = jugador2
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None  # 1, 2, o None (empate)

    def __post_init__(self):
        if self.board is None:
            self.board = [0] * (self.width * self.height)

    def clone(self):
        return ConnectFourGameState(
            width=self.width,
            height=self.height,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def get(self, x: int, y: int) -> int:
        # x: 0..width-1, y: 0..height-1 (0 es arriba)
        return self.board[y * self.width + x]

    def set(self, x: int, y: int, value: int):
        self.board[y * self.width + x] = value


# ============================================================
# 2. Acción (tirar ficha en una columna)
# ============================================================

@dataclass
class DropPieceAction:
    column: int
    player: int


# ============================================================
# 3. Forward Model
# ============================================================

class ConnectFourForwardModel:
    WIN_LEN = 4

    def compute_available_actions(self, state: ConnectFourGameState) -> List[DropPieceAction]:
        if state.is_terminal:
            return []

        actions = []
        for col in range(state.width):
            # si la celda superior está vacía, la columna acepta ficha
            if state.get(col, 0) == 0:
                actions.append(DropPieceAction(col, state.current_player))
        return actions

    def advance(self, state: ConnectFourGameState, action: DropPieceAction):
        if state.is_terminal:
            return

        col = action.column

        # validar columna (por seguridad)
        if not (0 <= col < state.width):
            return

        # si la columna está llena, no hacemos nada (en un juego real lanzarías excepción)
        if state.get(col, 0) != 0:
            return

        # gravedad: colocar en la fila más baja libre
        placed_y = None
        for y in range(state.height - 1, -1, -1):
            if state.get(col, y) == 0:
                state.set(col, y, action.player)
                placed_y = y
                break

        # si por alguna razón no se colocó, salir
        if placed_y is None:
            return

        # comprobar victoria desde la última ficha (más eficiente)
        if self.check_win_from_cell(state, action.player, col, placed_y):
            state.is_terminal = True
            state.winner = action.player
            return

        # empate: tablero lleno (no hay 0s)
        if all(v != 0 for v in state.board):
            state.is_terminal = True
            state.winner = None
            return

        # cambiar turno
        state.current_player = 1 if state.current_player == 2 else 2

    def check_win_from_cell(self, state: ConnectFourGameState, player: int, x: int, y: int) -> bool:
        # Cuenta consecutivas en ambas direcciones para cada vector
        directions = [
            (1, 0),   # horizontal
            (0, 1),   # vertical
            (1, 1),   # diagonal ↘
            (1, -1),  # diagonal ↗
        ]

        for dx, dy in directions:
            count = 1  # incluye (x,y)

            # hacia +dx, +dy
            nx, ny = x + dx, y + dy
            while 0 <= nx < state.width and 0 <= ny < state.height and state.get(nx, ny) == player:
                count += 1
                nx += dx
                ny += dy

            # hacia -dx, -dy
            nx, ny = x - dx, y - dy
            while 0 <= nx < state.width and 0 <= ny < state.height and state.get(nx, ny) == player:
                count += 1
                nx -= dx
                ny -= dy

            if count >= self.WIN_LEN:
                return True

        return False


# ============================================================
# 4. Utilidades de consola
# ============================================================

def print_board(state: ConnectFourGameState):
    symbols = {0: ".", 1: "X", 2: "O"}

    for y in range(state.height):
        row = [symbols[state.get(x, y)] for x in range(state.width)]
        print(" ".join(row))

    # índice de columnas para jugar
    print(" ".join(str(i) for i in range(state.width)))
    print()


def play_random_game():
    state = ConnectFourGameState(width=7, height=6)
    model = ConnectFourForwardModel()

    print("Estado inicial (4 en raya):")
    print_board(state)

    while not state.is_terminal:
        actions = model.compute_available_actions(state)
        action = random.choice(actions)
        model.advance(state, action)

        print(f"Jugador {action.player} tira en columna {action.column}")
        print_board(state)

    if state.winner is None:
        print("Empate 🤝")
    else:
        print(f"Gana el jugador {state.winner} 🎉")


if __name__ == "__main__":
    play_random_game()
