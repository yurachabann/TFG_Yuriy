from dataclasses import dataclass

from generic.game_action import GameAction


# Una acción guarda la casilla de origen, la de destino y el jugador.
@dataclass
class MovePieceAction(GameAction):
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    player: int

