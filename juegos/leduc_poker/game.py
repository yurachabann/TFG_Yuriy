from generic.imperfect.game import ImperfectGame

from .actions import PokerAction, PokerActionType
from .console import (
    print_action_result,
    print_action_summary,
    print_ai_action,
    print_board,
    read_human_move
)
from .forward_model import LeducPokerForwardModel
from .game_state import LeducPokerGameState


class LeducPokerGame(ImperfectGame):

    def __init__(self):
        super().__init__("Leduc Poker")
        self.num_players = 2

    def create_state(self):
        state = LeducPokerGameState(num_players=self.num_players)
        model = self.create_model()
        model.setup_game(state)
        return state

    def create_model(self):
        return LeducPokerForwardModel()

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(
        self,
        move: PokerActionType,
        player_id: int
    ):
        return PokerAction(
            action_type=move,
            player=player_id
        )

    def print_board(self, state):
        print_board(state)

    def print_action_summary(
        self,
        action: PokerAction,
        state_before: LeducPokerGameState
    ):
        print_action_summary(action, state_before)

    def print_action_result(
        self,
        state_before: LeducPokerGameState,
        action: PokerAction,
        state_after: LeducPokerGameState
    ):
        print_action_result(state_before, action, state_after)

    def print_ai_action(self, action: PokerAction):
        print_ai_action(action)
