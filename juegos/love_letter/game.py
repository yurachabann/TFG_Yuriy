from generic.imperfect.game import ImperfectGame
from .actions import PlayCardAction
from .console import print_board, read_human_move
from .forward_model import LoveLetterForwardModel
from .game_state import LoveLetterGameState


class LoveLetterGame(ImperfectGame):
    """
    Wrapper que integra Love Letter en el framework de información imperfecta.
    Solo conecta componentes.[cite: 9]
    """

    def __init__(self, num_players: int = 2):
        super().__init__("Love Letter")
        self.num_players = num_players

    def create_state(self):
        state = LoveLetterGameState(num_players=self.num_players)
        model = self.create_model()
        model.setup_game(state)
        return state

    def create_model(self):
        return LoveLetterForwardModel()
    

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        card, target, guess = move
        return PlayCardAction(
            card=card, player=player_id, target=target, guess=guess
        )

    def print_board(self, state):
        print_board(state)

    def print_ai_action(self, action: PlayCardAction):
        print(
          f"IA (Jugador {action.player}) juega: {action.card.name}"
           + (f" a Jugador {action.target}" if action.target is not None else "")
        )