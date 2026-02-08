from dataclasses import dataclass
from typing import List, Optional
import random

# ============================================================
# 1. Estado del juego
# ============================================================

@dataclass
class TicTacToeGameState:
    grid_size: int = 3
    board: List[int] = None  # 0 = vacío, 1 = jugador1, 2 = jugador2
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None  # 1, 2, o None

    def __post_init__(self):
        if self.board is None:
            self.board = [0] * (self.grid_size * self.grid_size)

    def clone(self):
        return TicTacToeGameState(
            grid_size=self.grid_size,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def get(self, x, y):
        return self.board[y * self.grid_size + x]

    def set(self, x, y, value):
        self.board[y * self.grid_size + x] = value


# ============================================================
# 2. Acción
# ============================================================

@dataclass
class SetCellAction:
    x: int
    y: int
    player: int


# ============================================================
# 3. Forward Model
# ============================================================

class TicTacToeForwardModel:

    def compute_available_actions(self, state: TicTacToeGameState) -> List[SetCellAction]:
        if state.is_terminal:
            return []

        actions = []
        for x in range(state.grid_size):
            for y in range(state.grid_size):
                if state.get(x, y) == 0:
                    actions.append(SetCellAction(x, y, state.current_player))
        return actions

    def advance(self, state: TicTacToeGameState, action: SetCellAction):
        if state.is_terminal:
            return

        state.set(action.x, action.y, action.player)

        if self.check_win(state, action.player):
            state.is_terminal = True
            state.winner = action.player
            return

        if all(v != 0 for v in state.board):
            state.is_terminal = True
            state.winner = None
            return

        state.current_player = 1 if state.current_player == 2 else 2

    def check_win(self, state: TicTacToeGameState, player: int) -> bool:
        g = state.grid_size

        for y in range(g):
            if all(state.get(x, y) == player for x in range(g)):
                return True

        for x in range(g):
            if all(state.get(x, y) == player for y in range(g)):
                return True

        if all(state.get(i, i) == player for i in range(g)):
            return True

        if all(state.get(g - 1 - i, i) == player for i in range(g)):
            return True

        return False


# ============================================================
# 4. Utilidades de consola (FUERA de la clase)
# ============================================================

def print_board(state: TicTacToeGameState):
    g = state.grid_size
    symbols = {0: ".", 1: "X", 2: "O"}

    for y in range(g):
        row = []
        for x in range(g):
            row.append(symbols[state.get(x, y)])
        print(" ".join(row))
    print()  # línea en blanco


def play_random_game():
    state = TicTacToeGameState()
    model = TicTacToeForwardModel()

    print("Estado inicial:")
    print_board(state)

    while not state.is_terminal:
        actions = model.compute_available_actions(state)
        action = random.choice(actions)
        model.advance(state, action)

        print(f"Jugador {action.player} juega en ({action.x}, {action.y})")
        print_board(state)

    if state.winner is None:
        print("Empate 🤝")
    else:
        print(f"Gana el jugador {state.winner} 🎉")


if __name__ == "__main__":
    play_random_game()
