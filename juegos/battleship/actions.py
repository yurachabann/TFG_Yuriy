from dataclasses import dataclass
from generic.game_action import GameAction

@dataclass(frozen=True)
class ShootAction(GameAction):
    player: int
    row: int
    col: int