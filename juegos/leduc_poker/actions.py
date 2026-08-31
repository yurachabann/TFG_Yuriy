from dataclasses import dataclass
from enum import Enum

from generic.game_action import GameAction


class PokerActionType(str, Enum):
    CHECK = "CHECK"
    BET = "BET"
    CALL = "CALL"
    RAISE = "RAISE"
    FOLD = "FOLD"


@dataclass(frozen=True)
class PokerAction(GameAction):
    action_type: PokerActionType
    player: int
