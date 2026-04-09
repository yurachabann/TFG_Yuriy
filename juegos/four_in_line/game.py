from core.game import Game

from juegos.four_in_line.four_in_line import (
    ConnectFourGameState,
    ConnectFourForwardModel,
    DropPieceAction,
    print_board,
    read_human_move,
)


class Connect4Game(Game):
    """
    Clase que integra 4 en raya con el framework.

    No contiene la lógica interna del juego.
    Solo expone una interfaz uniforme para que Match,
    Players y MatchRunner puedan trabajar con este juego.
    """

    def __init__(self):
        super().__init__("4 en raya")

    def create_state(self):
        """
        Crea y devuelve el estado inicial del juego.
        """
        return ConnectFourGameState()

    def create_model(self):
        """
        Crea y devuelve el forward model del juego.
        """
        return ConnectFourForwardModel()

    def read_human_move(self, state):
        """
        Lee un movimiento válido del jugador humano.
        En 4 en raya, el movimiento es una columna (int).
        """
        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        """
        Convierte el movimiento humano en una acción del dominio.
        """
        return DropPieceAction(move, player_id)

    def print_board(self, state):
        """
        Muestra el tablero por consola.
        """
        print_board(state)

    def print_ai_action(self, action):
        """
        Muestra la acción elegida por la IA.
        """
        print("IA juega columna:", action.column)