from .game_state import ConnectFourGameState
from .actions import DropPieceAction

from generic.forward_model import ForwardModel


class ConnectFourForwardModel(
    ForwardModel[ConnectFourGameState, DropPieceAction]
):
    WIN_LEN = 4

    def compute_available_actions(
        self,
        state: ConnectFourGameState
    ) -> list[DropPieceAction]:

        if state.is_terminal:
            return []

        actions = []

        for col in range(state.width):
            if state.get(col, 0) == 0:
                actions.append(
                    DropPieceAction(
                        col,
                        state.current_player
                    )
                )

        return actions

    def advance(
        self,
        state: ConnectFourGameState,
        action: DropPieceAction
    ) -> None:

        if state.is_terminal:
            return

        if action.player != state.current_player:
            raise ValueError(
                f"Turno inválido: action.player={action.player}, "
                f"pero current_player={state.current_player}."
            )

        if action not in self.compute_available_actions(state):
            raise ValueError(f"Acción no válida: {action}")

        col = action.column

        placed_y = None

        for y in range(state.height - 1, -1, -1):
            if state.get(col, y) == 0:
                state.set(col, y, action.player)
                placed_y = y
                break

        if placed_y is None:
            return

        if self.check_win_from_cell(
            state,
            action.player,
            col,
            placed_y
        ):
            state.is_terminal = True
            state.winner = action.player
            return

        if all(value != 0 for value in state.board):
            state.is_terminal = True
            state.winner = None
            return

        state.current_player = (
            1 if state.current_player == 2 else 2
        )

    def evaluate_terminal(
        self,
        state: ConnectFourGameState,
        ai_player: int,
        depth: int
    ) -> int:

        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 100000 - depth

        return -100000 + depth

    def check_win_from_cell(
        self,
        state: ConnectFourGameState,
        player: int,
        x: int,
        y: int
    ) -> bool:

        directions = [
            (1, 0),
            (0, 1),
            (1, 1),
            (1, -1),
        ]

        for dx, dy in directions:

            count = 1

            nx = x + dx
            ny = y + dy

            while (
                0 <= nx < state.width
                and 0 <= ny < state.height
                and state.get(nx, ny) == player
            ):
                count += 1
                nx += dx
                ny += dy

            nx = x - dx
            ny = y - dy
            while (
                0 <= nx < state.width
                and 0 <= ny < state.height
                and state.get(nx, ny) == player
            ):
                count += 1
                nx -= dx
                ny -= dy

            if count >= self.WIN_LEN:
                return True

        return False