from dataclasses import dataclass, field
from typing import Optional
from generic.imperfect.information_state import InformationState
from .cards import Card

@dataclass
class LoveLetterInformationState(InformationState):
    observer_id: int
    hand: list[Card]
    played_cards: dict[int, list[Card]]
    protected: dict[int, bool]
    eliminated: dict[int, bool]
    known_cards: dict[int, dict[int, Optional[Card]]]
    excluded_cards: dict[int, dict[int, list[Card]]]
    deck_count: int
    current_player: int