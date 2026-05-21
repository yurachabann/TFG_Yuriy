from core.game import Game

from juegos.checkers.checkers import (
    CheckersGameState,
    CheckersForwardModel,
    MovePieceAction,
    print_board,
    read_human_move,
)


class CheckersGame(Game):
    """
    Clase que integra damas con el framework.

    No contiene la lógica interna del juego.
    Solo adapta damas a:
    - Match
    - Players
    - MatchRunner
    - algoritmos de IA
    """

    def __init__(self):
        super().__init__("Damas")

    def create_state(self):
        return CheckersGameState()

    def create_model(self):
        return CheckersForwardModel()

    def read_human_move(self, state):
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        return MovePieceAction(move, player_id)

    def print_board(self, state):
        print_board(state)

    def print_ai_action(self, action):
        print("IA juega:", action.path)