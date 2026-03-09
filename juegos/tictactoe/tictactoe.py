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
    grid_size: int = 3
    board: list[int] = None
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None

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
# ACTION
# ============================================================

@dataclass
class SetCellAction(GameAction):
    x: int
    y: int
    player: int


# ============================================================
# FORWARD MODEL
# ============================================================

class TicTacToeForwardModel(ForwardModel[TicTacToeGameState, SetCellAction]):

    def compute_available_actions(self, state: TicTacToeGameState) -> list[SetCellAction]:

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


    def evaluate_terminal(self, state: TicTacToeGameState, ai_player: int, depth: int) -> int:

        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 10 - depth

        return -10 + depth


    def check_win(self, state: TicTacToeGameState, player: int):

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
# CONSOLE
# ============================================================

def print_board(state: TicTacToeGameState):

    symbols = {0: ".", 1: "X", 2: "O"}
    g = state.grid_size

    print()

    # Header de columnas (x)
    print("    ", end="")
    for x in range(g):
        print(f"{x} ", end="")
    print()

    for y in range(g):
        # Mostrar número de fila (y)
        print(f"{y} | ", end="")

        for x in range(g):
            print(symbols[state.get(x, y)], end=" ")

        print()

    print()


def read_human_move(state: TicTacToeGameState):

    while True:

        try:
            print("Enter move as: x y  (example: 1 2)")
            x, y = map(int, input("Move (x y): ").split())

        except ValueError:
            print("Invalid format. Example: 1 2")
            continue

        g = state.grid_size

        if not (0 <= x < g and 0 <= y < g):
            print("Out of range")
            continue

        if state.get(x, y) == 0:
            return x, y

        print("Cell occupied")


# ============================================================
# GAME LOOP
# ============================================================

def play_human_vs_ai(choose_move_fn, algorithm_name: str):

    state = TicTacToeGameState()
    model = TicTacToeForwardModel()

    human = 1
    ai = 2

    total_nodes_visited = 0
    total_cutoffs = 0
    max_depth_reached = 0
    total_elapsed_time = 0.0
    ai_turns = 0

    print(f"\n=== TicTacToe using {algorithm_name} ===")
    print_board(state)

    while not state.is_terminal:

        if state.current_player == human:

            x, y = read_human_move(state)

            model.advance(state, SetCellAction(x, y, human))

        else:

            action, stats = choose_move_fn(state, model, ai)

            total_nodes_visited += stats.nodes_visited
            total_cutoffs += stats.cutoffs
            total_elapsed_time += stats.elapsed_time
            max_depth_reached = max(max_depth_reached, stats.max_depth)
            ai_turns += 1

            model.advance(state, action)

            print("AI plays:", action.x, action.y)

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
