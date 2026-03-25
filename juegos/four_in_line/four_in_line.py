from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from generic.forward_model import ForwardModel, GameState, GameAction

# 1. Estado del juego

@dataclass
class ConnectFourGameState(GameState):
    width: int = 7
    height: int = 6
    board: Optional[list[int]] = None   # 0 = vacío, 1 = jugador 1, 2 = jugador 2
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None        # 1, 2 o None si es empate

    def __post_init__(self):
        if self.board is None:
            self.board = [0] * (self.width * self.height)

    def clone(self) -> "ConnectFourGameState":
        return ConnectFourGameState(
            width=self.width,
            height=self.height,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def get(self, x: int, y: int) -> int:
        return self.board[y * self.width + x]

    def set(self, x: int, y: int, value: int) -> None:
        self.board[y * self.width + x] = value

# 2. Acción

@dataclass
class DropPieceAction(GameAction):
    column: int
    player: int

# 3. Forward model

class ConnectFourForwardModel(ForwardModel[ConnectFourGameState, DropPieceAction]):
    WIN_LEN = 4

    def compute_available_actions(self, state: ConnectFourGameState) -> list[DropPieceAction]:
        if state.is_terminal:
            return []

        actions: list[DropPieceAction] = []
        for col in range(state.width):
            # Si la celda superior está vacía, se puede jugar en esa columna
            if state.get(col, 0) == 0:
                actions.append(DropPieceAction(col, state.current_player))

        return actions

    def advance(self, state: ConnectFourGameState, action: DropPieceAction) -> None:
        if state.is_terminal:
            return

        col = action.column

        # Validación de columna
        if not (0 <= col < state.width):
            return

        # Si la columna está llena, no hacemos nada
        if state.get(col, 0) != 0:
            return

        # Colocar ficha en la fila más baja libre
        placed_y = None
        for y in range(state.height - 1, -1, -1):
            if state.get(col, y) == 0:
                state.set(col, y, action.player)
                placed_y = y
                break

        if placed_y is None:
            return

        # Comprobar victoria
        if self.check_win_from_cell(state, action.player, col, placed_y):
            state.is_terminal = True
            state.winner = action.player
            return

        # Empate
        if all(value != 0 for value in state.board):
            state.is_terminal = True
            state.winner = None
            return

        # Cambiar turno
        state.current_player = 1 if state.current_player == 2 else 2

    def evaluate_terminal(self, state: ConnectFourGameState, ai_player: int, depth: int) -> int:
        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 100000 - depth

        return -100000 + depth

    def evaluate_heuristic(self, state: ConnectFourGameState, ai_player: int) -> int:
        opponent = 1 if ai_player == 2 else 2
        score = 0

        # Bonus por controlar el centro
        center_col = state.width // 2
        center_values = [state.get(center_col, y) for y in range(state.height)]
        score += center_values.count(ai_player) * 6
        score -= center_values.count(opponent) * 6

        # Horizontales
        for y in range(state.height):
            for x in range(state.width - 3):
                window = [state.get(x + i, y) for i in range(4)]
                score += self.evaluate_window(window, ai_player, opponent)

        # Verticales
        for x in range(state.width):
            for y in range(state.height - 3):
                window = [state.get(x, y + i) for i in range(4)]
                score += self.evaluate_window(window, ai_player, opponent)

        # Diagonales pabajo
        for x in range(state.width - 3):
            for y in range(state.height - 3):
                window = [state.get(x + i, y + i) for i in range(4)]
                score += self.evaluate_window(window, ai_player, opponent)

        # Diagonales parriba
        for x in range(state.width - 3):
            for y in range(3, state.height):
                window = [state.get(x + i, y - i) for i in range(4)]
                score += self.evaluate_window(window, ai_player, opponent)

        return score

    def evaluate_window(self, window: list[int], ai_player: int, opponent: int) -> int:
        score = 0

        ai_count = window.count(ai_player)
        opp_count = window.count(opponent)
        empty_count = window.count(0)

        # Casos favorables para la IA
        if ai_count == 4:
            score += 10000
        elif ai_count == 3 and empty_count == 1:
            score += 100
        elif ai_count == 2 and empty_count == 2:
            score += 10

        # Casos peligrosos del rival
        if opp_count == 4:
            score -= 10000
        elif opp_count == 3 and empty_count == 1:
            score -= 120
        elif opp_count == 2 and empty_count == 2:
            score -= 12

        return score

    def check_win_from_cell(
        self,
        state: ConnectFourGameState,
        player: int,
        x: int,
        y: int
    ) -> bool:
        directions = [
            (1, 0),   # horizontal
            (0, 1),   # vertical
            (1, 1),   # diagonal pabajo
            (1, -1),  # diagonal parriba
        ]

        for dx, dy in directions:
            count = 1

            # Hacia delante
            nx, ny = x + dx, y + dy
            while 0 <= nx < state.width and 0 <= ny < state.height and state.get(nx, ny) == player:
                count += 1
                nx += dx
                ny += dy

            # Hacia atrás
            nx, ny = x - dx, y - dy
            while 0 <= nx < state.width and 0 <= ny < state.height and state.get(nx, ny) == player:
                count += 1
                nx -= dx
                ny -= dy

            if count >= self.WIN_LEN:
                return True

        return False

# 4. Utilidades de consola

def print_board(state: ConnectFourGameState) -> None:
    symbols = {0: ".", 1: "X", 2: "O"}

    print()
    for y in range(state.height):
        row = [symbols[state.get(x, y)] for x in range(state.width)]
        print(f"{y} | " + " ".join(row))

    print("    " + " ".join(str(i) for i in range(state.width)))
    print()


def read_human_move(state: ConnectFourGameState) -> int:
    while True:
        try:
            print("Enter move as: column (example: 3)")
            col = int(input("Move (column): ").strip())
        except ValueError:
            print("Invalid format. Example: 3")
            continue

        if not (0 <= col < state.width):
            print("Out of range")
            continue

        if state.get(col, 0) != 0:
            print("Column full")
            continue

        return col

# 5. Bucle de juego

def play_human_vs_ai(choose_move_fn, algorithm_name: str) -> None:
    state = ConnectFourGameState(width=7, height=6)
    model = ConnectFourForwardModel()

    human = 1
    ai = 2

    total_nodes_visited = 0
    total_cutoffs = 0
    max_depth_reached = 0
    total_elapsed_time = 0.0
    ai_turns = 0

    print(f"\n=== Connect Four using {algorithm_name} ===")
    print_board(state)

    while not state.is_terminal:
        if state.current_player == human:
            col = read_human_move(state)
            model.advance(state, DropPieceAction(col, human))
        else:
            action, stats = choose_move_fn(state, model, ai)

            total_nodes_visited += stats.nodes_visited
            total_cutoffs += stats.cutoffs
            total_elapsed_time += stats.elapsed_time
            max_depth_reached = max(max_depth_reached, stats.max_depth)
            ai_turns += 1

            model.advance(state, action)
            print("AI plays column:", action.column)

        print_board(state)

    if state.winner is None:
        print("Draw")
    elif state.winner == human:
        print("You win")
    else:
        print("AI wins")

    print("\n=== Search statistics ===")
    print("Algorithm:", algorithm_name)
    print("AI turns:", ai_turns)
    print("Total nodes visited:", total_nodes_visited)
    print("Total cutoffs:", total_cutoffs)
    print("Max depth reached:", max_depth_reached)
    print("Total elapsed time:", total_elapsed_time)

    if ai_turns > 0:
        print("Average time per AI turn:", total_elapsed_time / ai_turns)