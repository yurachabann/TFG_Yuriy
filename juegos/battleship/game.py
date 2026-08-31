from generic.imperfect.game import ImperfectGame
from .actions import ShootAction
from .console import print_board, read_human_move, print_ai_action, print_action_summary, print_action_result
from .forward_model import BattleshipForwardModel
from .game_state import BattleshipGameState


class BattleshipGame(ImperfectGame):
    def __init__(self, grid_size: int = 10):
        super().__init__("Battleship")
        self.grid_size = grid_size

    def create_state(self):
        state = BattleshipGameState(grid_size=self.grid_size)
        model = self.create_model()
        model.setup_game(state)
        return state

    def create_model(self):
        return BattleshipForwardModel()

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        row, col = move
        return ShootAction(player=player_id, row=row, col=col)

    def print_board(self, state):
        print_board(state)

    def print_action_summary(self, action: ShootAction, state_before: BattleshipGameState):
        print_action_summary(action, state_before)

    def print_action_result(self, state_before: BattleshipGameState, action: ShootAction, state_after: BattleshipGameState):
        print_action_result(state_before, action, state_after)

    def print_ai_action(self, action: ShootAction):
        print_ai_action(action)