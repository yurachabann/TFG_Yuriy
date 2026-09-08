from __future__ import annotations

from core.players.player import Player


class HumanPlayer(Player):
    """
    Jugador humano.

    1. Le pide al juego que lea el movimiento por consola
    2. Convierte ese movimiento en una acción del dominio
    3. Devuelve la acción, pero no modifica el estado

    - HumanPlayer NO avanza el estado
    - Solo decide qué acción quiere hacer
    - Quien aplica la acción es Match
    """

    def __init__(self, name: str, player_id: int):
        super().__init__(name=name, player_id=player_id)

    def choose_action(self, state, game):
        move = game.read_human_move(state)
        action = game.create_action_from_move(move, self.player_id)
        return action, None

    def is_human(self) -> bool:
        return True