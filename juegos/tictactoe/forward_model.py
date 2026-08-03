from generic.forward_model import ForwardModel

from .actions import SetCellAction
from .constants import EMPTY, PLAYER_1, PLAYER_2
from .game_state import TicTacToeGameState


class TicTacToeForwardModel(
    ForwardModel[TicTacToeGameState, SetCellAction]
):

    def compute_available_actions(
        self,
        state: TicTacToeGameState
    ) -> list[SetCellAction]:

        if state.is_terminal:
            return []

        actions = []

        for y in range(state.grid_size):
            for x in range(state.grid_size):
                if state.get(x, y) == EMPTY:
                    actions.append(
                        SetCellAction(
                            x=x,
                            y=y,
                            player=state.current_player
                        )
                    )

        return actions

    def advance(
        self,
        state: TicTacToeGameState,
        action: SetCellAction
    ) -> None:

        if state.is_terminal:
            return

        if state.get(action.x, action.y) != EMPTY:
            raise ValueError(
                f"La celda ({action.x}, {action.y}) ya está ocupada."
            )

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

        if all(cell != EMPTY for cell in state.board):
            state.is_terminal = True
            state.winner = None
            return

        state.current_player = (
            PLAYER_1
            if state.current_player == PLAYER_2
            else PLAYER_2
        )

    def evaluate_terminal(
        self,
        state: TicTacToeGameState,
        ai_player: int,
        depth: int
    ) -> int:

        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 10 - depth

        return -10 + depth

    def check_win(
        self,
        state: TicTacToeGameState,
        player: int
    ) -> bool:

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