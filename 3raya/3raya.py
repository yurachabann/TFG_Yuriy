from dataclasses import dataclass
from typing import List, Optional, Tuple
import random

# ============================================================
# 1. Estado del juego
# ============================================================

@dataclass
class TicTacToeGameState:
    grid_size: int = 3
    board: List[int] = None  # 0 = vacío, 1 = X, 2 = O
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None  # 1, 2 o None (empate)

    def __post_init__(self):
        if self.board is None:
            self.board = [0] * (self.grid_size * self.grid_size)

    def clone(self):
        # Copia para simular jugadas sin modificar el estado real
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

        # Aplicar jugada
        state.set(action.x, action.y, action.player)

        # Comprobar victoria
        if self.check_win(state, action.player):
            state.is_terminal = True
            state.winner = action.player
            return

        # Comprobar empate
        if all(v != 0 for v in state.board):
            state.is_terminal = True
            state.winner = None
            return

        # Cambiar turno
        state.current_player = 1 if state.current_player == 2 else 2

    def check_win(self, state: TicTacToeGameState, player: int) -> bool:
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
# 4. Consola
# ============================================================

def print_board(state: TicTacToeGameState):
    symbols = {0: ".", 1: "X", 2: "O"}
    g = state.grid_size
    for y in range(g):
        print(" ".join(symbols[state.get(x, y)] for x in range(g)))
    print()


# ============================================================
# 5. Minimax (puro)
# ============================================================

def evaluate_terminal(state: TicTacToeGameState, ai_player: int, depth: int) -> int:
    """
    Puntuación desde la perspectiva de la IA.
    depth hace que prefiera ganar rápido y retrasar perder.
    """
    if state.winner is None:
        return 0
    if state.winner == ai_player:
        return 10 - depth
    return -10 + depth


def minimax(state: TicTacToeGameState, model: TicTacToeForwardModel, ai_player: int, depth: int = 0) -> Tuple[int, Optional[SetCellAction]]:
    """
    Devuelve (mejor_score, mejor_accion) para el jugador al que le toca en state.current_player.

    - Si le toca a la IA: elige la jugada con score máximo.
    - Si le toca al rival: elige la jugada con score mínimo (lo peor para la IA).
    """
    # Caso base: si terminó el juego, devolvemos la evaluación
    if state.is_terminal:
        return evaluate_terminal(state, ai_player, depth), None

    actions = model.compute_available_actions(state)
    if not actions:
        return 0, None

    is_ai_turn = (state.current_player == ai_player)

    if is_ai_turn:
        best_score = -10**9
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = minimax(next_state, model, ai_player, depth + 1)

            if score > best_score:
                best_score = score
                best_action = action

        return best_score, best_action

    else:
        best_score = 10**9
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = minimax(next_state, model, ai_player, depth + 1)

            if score < best_score:
                best_score = score
                best_action = action

        return best_score, best_action


def choose_ai_move(state: TicTacToeGameState, model: TicTacToeForwardModel, ai_player: int) -> SetCellAction:
    # Elegimos la mejor acción llamando a minimax
    score, action = minimax(state, model, ai_player, depth=0)

    # Por seguridad, si algo raro pasa, jugamos una acción válida al azar
    if action is None:
        return random.choice(model.compute_available_actions(state))

    return action


# ============================================================
# 6. Humano vs IA
# ============================================================

def read_human_move(state: TicTacToeGameState) -> Tuple[int, int]:
    g = state.grid_size
    while True:
        raw = input(f"Tu jugada (x y) entre 0 y {g-1}: ").strip()
        parts = raw.split()

        if len(parts) != 2:
            print("Formato inválido. Ejemplo: 1 2")
            continue

        try:
            x, y = int(parts[0]), int(parts[1])
        except ValueError:
            print("Debes introducir enteros.")
            continue

        if not (0 <= x < g and 0 <= y < g):
            print("Fuera de rango.")
            continue

        if state.get(x, y) != 0:
            print("Casilla ocupada.")
            continue

        return x, y


def play_human_vs_ai(human_player: int = 1):
    state = TicTacToeGameState()
    model = TicTacToeForwardModel()
    ai_player = 2 if human_player == 1 else 1

    print("=== TicTacToe: Humano vs IA (Minimax) ===")
    print(f"Tú: {'X' if human_player == 1 else 'O'} | IA: {'X' if ai_player == 1 else 'O'}")
    print("Coordenadas: x=columna, y=fila (0..2). Empieza X.")
    print()
    print_board(state)

    while not state.is_terminal:
        if state.current_player == human_player:
            x, y = read_human_move(state)
            model.advance(state, SetCellAction(x, y, human_player))
            print(f"Tú juegas en ({x}, {y})")
            print_board(state)
        else:
            action = choose_ai_move(state, model, ai_player)
            model.advance(state, action)
            print(f"IA juega en ({action.x}, {action.y})")
            print_board(state)

    if state.winner is None:
        print("Empate 🤝")
    elif state.winner == human_player:
        print("¡Ganaste! 🎉")
    else:
        print("Gana la IA 🤖🎉")


if __name__ == "__main__":
    # Cambia a 2 si quieres ser O en vez de X
    play_human_vs_ai(human_player=1)
