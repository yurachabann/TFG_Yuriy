from dataclasses import dataclass, field
from typing import Optional

from generic.imperfect.game_state import ImperfectGameState
from .cards import Card


@dataclass
class LeducPokerGameState(ImperfectGameState):
    num_players: int = 2

    # Cartas todavía no utilizadas. Al terminar la primera ronda se extrae
    # de aquí la única carta pública de la partida.
    deck: list[Card] = field(default_factory=list)

    # Cada jugador recibe exactamente una carta privada.
    private_cards: dict[int, Optional[Card]] = field(default_factory=dict)

    # Carta común que se revela entre la primera y la segunda ronda.
    public_card: Optional[Card] = None

    current_player: int = 1
    betting_round: int = 1

    # Fichas aportadas durante toda la mano, incluyendo el ante inicial.
    contributions: dict[int, int] = field(default_factory=dict)

    # Fichas aportadas solamente durante la ronda de apuestas actual.
    round_contributions: dict[int, int] = field(default_factory=dict)

    # Mayor contribución de la ronda que el otro jugador debe igualar.
    current_bet: int = 0

    # Número de apuestas agresivas de la ronda: BET o RAISE.
    # El máximo estándar usado aquí es 2: una apuesta y una subida.
    bets_in_round: int = 0

    # Permite detectar CHECK-CHECK, que finaliza la ronda.
    consecutive_checks: int = 0

    # Historial público de acciones. Forma parte del InformationState porque
    # en Poker la secuencia de apuestas contiene información estratégica.
    action_history: list[str] = field(default_factory=list)

    is_terminal: bool = False
    winner: Optional[int] = None
    folded_player: Optional[int] = None
    last_action_summary: Optional[str] = None

    def __post_init__(self):
        if self.num_players != 2:
            raise ValueError("Leduc Poker está implementado para exactamente 2 jugadores.")

        if not self.private_cards:
            self.private_cards = {1: None, 2: None}

        if not self.contributions:
            self.contributions = {1: 0, 2: 0}

        if not self.round_contributions:
            self.round_contributions = {1: 0, 2: 0}

    @property
    def pot(self) -> int:
        return sum(self.contributions.values())

    def clone(self):
        return LeducPokerGameState(
            num_players=self.num_players,
            deck=self.deck.copy(),
            private_cards=self.private_cards.copy(),
            public_card=self.public_card,
            current_player=self.current_player,
            betting_round=self.betting_round,
            contributions=self.contributions.copy(),
            round_contributions=self.round_contributions.copy(),
            current_bet=self.current_bet,
            bets_in_round=self.bets_in_round,
            consecutive_checks=self.consecutive_checks,
            action_history=self.action_history.copy(),
            is_terminal=self.is_terminal,
            winner=self.winner,
            folded_player=self.folded_player,
            last_action_summary=self.last_action_summary
        )
