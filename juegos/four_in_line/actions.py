from dataclasses import dataclass

from generic.game_action import GameAction


@dataclass
class DropPieceAction(GameAction):
    column: int
    player: int