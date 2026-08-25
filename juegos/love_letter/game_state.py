from dataclasses import dataclass, field
from typing import Optional
from generic.imperfect.game_state import ImperfectGameState
from .cards import Card

@dataclass
class LoveLetterGameState(ImperfectGameState):
    num_players: int = 2
    deck: list[Card] = field(default_factory=list)
    hands: dict[int, list[Card]] = field(default_factory=dict)
    played_cards: dict[int, list[Card]] = field(default_factory=dict)
    protected: dict[int, bool] = field(default_factory=dict)
    eliminated: dict[int, bool] = field(default_factory=dict)
    known_cards: dict[int, dict[int, Optional[Card]]] = field(default_factory=dict)
    excluded_cards: dict[int, dict[int, set[Card]]] = field(default_factory=dict)
    current_player: int = 1  # <-- Cambiado de 0 a 1
    is_terminal: bool = False
    winner: Optional[int] = None
    removed_card: Optional[Card] = None

    def __post_init__(self):
        if not self.hands:
            self.hands = {i: [] for i in range(1, self.num_players + 1)}
            self.played_cards = {i: [] for i in range(1, self.num_players + 1)}
            self.protected = {i: False for i in range(1, self.num_players + 1)}
            self.eliminated = {i: False for i in range(1, self.num_players + 1)}
        if not self.known_cards:
            self.known_cards = {
                i: {j: None for j in range(1, self.num_players + 1)}
                for i in range(1, self.num_players + 1)
            }
        if not self.excluded_cards:
            self.excluded_cards = {
                i: {j: set() for j in range(1, self.num_players + 1)}
                for i in range(1, self.num_players + 1)
            }

    def clone(self):
        return LoveLetterGameState(
            num_players=self.num_players,
            deck=self.deck.copy(),
            hands={p: h.copy() for p, h in self.hands.items()},
            played_cards={p: pc.copy() for p, pc in self.played_cards.items()},
            protected=self.protected.copy(),
            eliminated=self.eliminated.copy(),
            known_cards={
                observer: known.copy()
                for observer, known in self.known_cards.items()
            },
            excluded_cards={
                observer: {
                    target: cards.copy()
                    for target, cards in excluded.items()
                }
                for observer, excluded in self.excluded_cards.items()
            },
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner,
            removed_card=self.removed_card
        )