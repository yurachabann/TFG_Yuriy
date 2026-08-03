from dataclasses import dataclass

from generic.game_action import GameAction


@dataclass
class SetCellAction(GameAction):
    x: int
    y: int
    player: int