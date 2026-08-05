from dataclasses import dataclass
from typing import Optional
from generic.game_action import GameAction
from .cards import Card

@dataclass(frozen=True)
class PlayCardAction(GameAction):
    card: Card
    player: int
    target: Optional[int] = None
    guess: Optional[Card] = None