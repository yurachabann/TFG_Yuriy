from dataclasses import dataclass
from typing import Optional

from generic.imperfect.information_state import InformationState
from .cards import Card


@dataclass
class LeducPokerInformationState(InformationState):
    """
    Información observable por un jugador de Leduc Poker.

    Incluye su propia carta privada y toda la información pública de la mano,
    pero nunca la carta privada del rival ni el orden de las cartas ocultas.
    """
    observer_id: int
    num_players: int
    private_card: Card
    public_card: Optional[Card]
    betting_round: int
    current_player: int
    contributions: dict[int, int]
    round_contributions: dict[int, int]
    current_bet: int
    bets_in_round: int
    consecutive_checks: int
    action_history: list[str]
    deck_count: int 
