from dataclasses import dataclass
from typing import List, Optional, Tuple
import random

#y=0   (0,0) (1,0) (2,0)
#y=1   (0,1) (1,1) (2,1)
#y=2   (0,2) (1,2) (2,2)

        #x=0   x=1   x=2

# ============================================================
# 1. Game State
# ============================================================

@dataclass
class TicTacToeGameState:
    grid_size: int = 3
    board: List[int] = None  # 0 = empty, 1 = X, 2 = O
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None  # 1, 2 or None (draw)

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
# 2. Action
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

        # Apply move
        state.set(action.x, action.y, action.player)

        # Check win
        if self.check_win(state, action.player):
            state.is_terminal = True
            state.winner = action.player
            return

        # Check draw
        if all(v != 0 for v in state.board):
            state.is_terminal = True
            state.winner = None
            return

        # Switch turn
        state.current_player = 1 if state.current_player == 2 else 2

    def check_win(self, state: TicTacToeGameState, player: int) -> bool:
        g = state.grid_size

        # Rows
        for y in range(g):
            if all(state.get(x, y) == player for x in range(g)):
                return True

        # Columns
        for x in range(g):
            if all(state.get(x, y) == player for y in range(g)):
                return True

        # Main diagonal
        if all(state.get(i, i) == player for i in range(g)):
            return True

        # Anti diagonal
        if all(state.get(g - 1 - i, i) == player for i in range(g)):
            return True

        return False


# ============================================================
# 4. Console Utils
# ============================================================

def print_board(state: TicTacToeGameState):
    symbols = {0: ".", 1: "X", 2: "O"}
    g = state.grid_size

    # Header de columnas (x)
    print("     ", end="")
    for x in range(g):
        print(f"x={x} ", end="")
    print("\n")

    for y in range(g):
        # Etiqueta de fila (y)
        print(f"y={y}  ", end="")

        # Contenido de la fila
        for x in range(g):
            print(f" {symbols[state.get(x, y)]}  ", end="")

        print()  # salto de línea

    print()

# ============================================================
# 5. Minimax (pure)
# ============================================================

def evaluate_terminal(state: TicTacToeGameState, ai_player: int, depth: int) -> int:
    """
    Score from the AI perspective.
    depth makes it prefer faster wins and slower losses.
    """
    if state.winner is None:
        return 0
    if state.winner == ai_player:
        return 10 - depth
    return -10 + depth


def minimax(
    state: TicTacToeGameState,
    model: TicTacToeForwardModel,
    ai_player: int,
    depth: int = 0
) -> Tuple[int, Optional[SetCellAction]]:
    """
    Returns (best_score, best_action) for the player to move in state.current_player.

    - If it's AI turn: maximize score.
    - If it's opponent turn: minimize score (worst for AI).
    """
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
    score, action = minimax(state, model, ai_player, depth=0)

    # Safety fallback
    if action is None:
        return random.choice(model.compute_available_actions(state))

    return action


# ============================================================
# 6. Human vs AI
# ============================================================

def read_human_move(state: TicTacToeGameState) -> Tuple[int, int]:
    g = state.grid_size
    while True:
        raw = input(f"Your move (x y) between 0 and {g-1}: ").strip()
        parts = raw.split()

        if len(parts) != 2:
            print("Invalid format. Example: 1 2")
            continue

        try:
            x, y = int(parts[0]), int(parts[1])
        except ValueError:
            print("You must enter integers.")
            continue

        if not (0 <= x < g and 0 <= y < g):
            print("Out of range.")
            continue

        if state.get(x, y) != 0:
            print("Cell occupied.")
            continue

        return x, y


def play_human_vs_ai(human_player: int = 1):
    state = TicTacToeGameState()
    model = TicTacToeForwardModel()
    ai_player = 2 if human_player == 1 else 1

    print("=== TicTacToe: Human vs AI (Minimax) ===")
    print(f"You: {'X' if human_player == 1 else 'O'} | AI: {'X' if ai_player == 1 else 'O'}")
    print("Coordinates: x=column, y=row (0..2). X starts.")
    print()
    print_board(state)

    while not state.is_terminal:
        if state.current_player == human_player:
            x, y = read_human_move(state)
            model.advance(state, SetCellAction(x, y, human_player))
            print(f"You play at ({x}, {y})")
            print_board(state)
        else:
            action = choose_ai_move(state, model, ai_player)
            model.advance(state, action)
            print(f"AI plays at ({action.x}, {action.y})")
            print_board(state)

    if state.winner is None:
        print("Draw 🤝")
    elif state.winner == human_player:
        print("You win! 🎉")
    else:
        print("AI wins 🤖🎉")


# ============================================================
# 7. NEW: AI vs AI (Minimax vs Minimax) test method
# ============================================================

def play_ai_vs_ai():
    state = TicTacToeGameState()
    model = TicTacToeForwardModel()

    print("=== TicTacToe: AI vs AI (Minimax vs Minimax) ===")
    print("Expected result with perfect play: Draw ✅")
    print()
    print_board(state)

    while not state.is_terminal:
        current_ai = state.current_player
        action = choose_ai_move(state, model, current_ai)
        model.advance(state, action)
        print(f"Player {current_ai} plays at ({action.x}, {action.y})")
        print_board(state)

    print("Final result:")
    if state.winner is None:
        print("Draw ✅")
    else:
        print(f"Winner: Player {state.winner} ❌ (unexpected if both are pure minimax)")


if __name__ == "__main__":
    # Run the new test method:
   # play_ai_vs_ai()

    # Or play human vs AI:
     play_human_vs_ai(human_player=1)  # change to 2 to play as O
